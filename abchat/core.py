# -*- coding: utf-8 -*-
import time

import gevent
from gevent.pool import Pool

from .mixins import MailBoxMixIn
from .container import WorkersContainerListType
from .log import log


# message type
MSG_TO_MASTER = 1
MSG_TO_CLIENT = 2


class ContinueFlag(object):pass


class Master(MailBoxMixIn, gevent.Greenlet):
    worker_kwargs = {'client_send_interval': None}

    def __init__(self, worker_class,
        worker_container_type=WorkersContainerListType,
        broadcast_backlog=50,
        dump_status_interval=60):
        """Master Contains All Connected Clients,
        And as a rount, to distribute messages from clients.

        Usage:
            master = Master(WorkerClass, WorkerContainerType, **kwargs)
            master.start()
            s = StreamServer(ADDRESS_TUPLE, master.handle)
            s.serve_forever()

        Two build-in WorkerClasses:
            abchat.LineWorker - For '\n' ending line based messages
            abchat.StreamWorker - For streaming message

            streaming message means NO delimiter to split message.
            so, the message scheme like below:
                +-------------+-------------+-------------+-------------+
                | 4 bytes int | binary data | 4 bytes int | binary data | ...
                +-------------+-------------+-------------+-------------+
            The value of 4 bytes int represent the binary data length after
            the 4 bytes.

            First, read 4 bytes from socket, and got it's value,
            Then, read the value length.
            And go on this loop, We can split message correctly

        Two build-in WorkerContainerType:
            abchat.container.WorkersContainerListType
                - keep all clients as list.
                  this type can only broadcast message to all connected clients

            abchat.containter.WorkersContainerDictType
                - keep all clients as dict,
                  this type can also send private message
        """
        self.workers = worker_container_type()
        self.worker_class = worker_class
        self.broadcast_backlog = broadcast_backlog
        self.dump_status_interval = dump_status_interval

        MailBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        gevent.spawn_later(1, self.dump_master_status)


    @classmethod
    def set_worker_kwargs(cls, **kwargs):
        cls.worker_kwargs.update(kwargs)

    def dump_master_status(self):
        while True:
            log.debug('workers amount: {0}'.format(self.workers.amount()))
            gevent.sleep(self.dump_status_interval)

    def handle(self, remote, address):
        self.worker_class(self, remote, address, **self.worker_kwargs).start()

    def _run(self):
        while True:
            gevent.sleep(0)
            message = self.inbox.get()
            gevent.spawn(self.emit_message, message)

    def emit_message(self, message):
        self.broadcast_message(message)

    def broadcast_message(self, message):
        pool = Pool(self.broadcast_backlog)
        pool.map_async(
            lambda w: self._worker_broadcast(w, message),
            self.workers.all_workers()
        ).start()

    def _worker_broadcast(self, w, message):
        w.receive(message, MSG_TO_CLIENT)
        

class BaseWorker(MailBoxMixIn, gevent.Greenlet):
    def __init__(self, master, sock, address, client_send_interval=None):
        """Can't Use BaseWorker directly,
        you can find the real worker at abchat/__init__.py
        """
        self.master = master
        self.sock = sock
        self.address = address
        self.client_send_interval = client_send_interval
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

            if data is ContinueFlag:
                continue

            if not data:
                break
            self.receive(data, MSG_TO_MASTER)

    def _inbox_get(self):
        while True:
            gevent.sleep(0)
            data = self.inbox.get()
            self.receive(data, MSG_TO_CLIENT)

    def check_interval(self, interval=None):
        interval = interval or self.client_send_interval
        if not interval:
            return None

        timestamp = getattr(self, 'timestamp', None)
        self.timestamp = time.time()
        if timestamp:
            if self.timestamp - timestamp < self.client_send_interval:
                return ContinueFlag


    def sock_recv(self):
        """In the method, you should call self.master.workers.add(*args)
        to add this worker in master's worker containter.
        And, you do this, just in condition of self.first_receive == True
        """
        raise NotImplemented()

    def receive(self, message, tp):
        if tp == MSG_TO_MASTER:
            self.master.put(message)
        elif tp == MSG_TO_CLIENT:
            try:
                self.sendall(message)
            except Exception as e:
                log.error("worker sendall error: {0}".format(str(e)))
                this = gevent.getcurrent()
                this.kill()
        else:
            log.error("worker receive, unknown tp: {0}".format(tp))


    def before_worker_exit(self):
        """In the method, you should call self.master.workers.rem(*args)"""
        raise NotImplemented()


    def _run(self):
        recv = gevent.spawn(self._sock_recv)
        get = gevent.spawn(self._inbox_get)

        def _clear(glet):
            glet.unlink(_clear)
            gevent.killall([recv, get])

        recv.link(_clear)
        get.link(_clear)
        gevent.joinall([recv, get])
        self.before_worker_exit()
        log.debug('{0} worker died'.format(self.address))
