# -*- coding: utf-8 -*-
import gevent

from .mixins import MailBoxMixIn
from .container import WorkersContainerListType

class InvalidData(object):pass


class Master(MailBoxMixIn, gevent.Greenlet):
    def __init__(self, worker_class, worker_container_type=WorkersContainerListType):
        self.workers = worker_container_type()
        self.worker_class = worker_class
        MailBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)

    def handle(self, remote, address):
        self.worker_class(self, remote).start()

    def _run(self):
        while True:
            gevent.sleep(0)
            message = self.inbox.get()
            self.emit_message(message)

    def emit_message(self, message):
        for w in self.workers.all_workers():
            w.put(message)
        

class BaseWorker(MailBoxMixIn, gevent.Greenlet):
    def __init__(self, master, sock):
        self.master = master
        self.sock = sock
        self.rfile = self.sock.makefile('rb')
        self.wfile = self.sock.makefile('wb')
        MailBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        self.first_receive = True
        print 'new worker'

    def _sock_recv(self):
        while True:
            gevent.sleep(0)
            data = self.sock_recv()
            if self.first_receive:
                self.first_receive = False
                continue

            if data is InvalidData:
                continue

            if not data:
                print 'connection lost'
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
            self.sendall(message)

    def _clear(self, *args):
        pass

    def _run(self):
        recv = gevent.spawn(self._sock_recv)
        get = gevent.spawn(self._inbox_get)

        def _clear(*args):
            self._clear(*args)
            get.kill()
        recv.link(_clear)
        gevent.joinall([recv, get])
        print 'worker died...'
