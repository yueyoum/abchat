# -*- coding: utf-8 -*-
import gevent

from .mixins import MailBoxMixIn
from .container import WorkersContainerListType
from .log import log

class InvalidData(object):pass


class Master(MailBoxMixIn, gevent.Greenlet):
    def __init__(self, worker_class, worker_container_type=WorkersContainerListType):
        self.workers = worker_container_type()
        self.worker_class = worker_class
        MailBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        gevent.spawn_later(1, self.dump_master_status)

    def dump_master_status(self):
        while True:
            log.debug('workers amount: {0}'.format(self.workers.amount()))
            gevent.sleep(60)

    def handle(self, remote, address):
        self.worker_class(self, remote, address).start()

    def _run(self):
        while True:
            gevent.sleep(0)
            message = self.inbox.get()
            self.emit_message(message)

    def emit_message(self, message):
        for w in self.workers.all_workers():
            w.put(message)
        

class BaseWorker(MailBoxMixIn, gevent.Greenlet):
    def __init__(self, master, sock, address):
        self.master = master
        self.sock = sock
        self.address = address
        MailBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        self.first_receive = True
        log.debug('{0} new worker'.format(self.address))

    def _sock_recv(self):
        while True:
            gevent.sleep(0)
            data = self.sock_recv()
            if self.first_receive:
                self.first_receive = False
                continue

            if data is InvalidData:
                log.warning('{0} got Invalid data'.format(self.address))
                continue

            if not data:
                break
            self.receive(data, 'sock')

    def _inbox_get(self):
        while True:
            gevent.sleep(0)
            data = self.inbox.get()
            self.receive(data, 'inbox')

    def sock_recv(self):
        """In the method, you should call self.master.workers.add()
        to add this worker in master's worker containter.
        And, you do this, just in condition of self.first_receive == True
        """
        raise NotImplemented()

    def receive(self, message, tp):
        if tp == 'sock':
            self.master.put(message)
        elif tp == 'inbox':
            try:
                self.sendall(message)
            except Exception as e:
                log.error("worker sendall error: {0}".format(str(e)))
                this = gevent.getcurrent()
                this.kill()
        else:
            log.error("worker receive, unknown tp: {0}".format(tp))


    def clear_worker(self, *args):
        pass

    def _run(self):
        recv = gevent.spawn(self._sock_recv)
        get = gevent.spawn(self._inbox_get)

        self._has_clear_worker = False
        def _clear(glet):
            glet.unlink(_clear)
            if not self._has_clear_worker:
                self._has_clear_worker = True
                self.clear_worker(glet)
            gevent.killall([recv, get])

        recv.link(_clear)
        get.link(_clear)
        gevent.joinall([recv, get])
        log.debug('{0} worker died'.format(self.address))
