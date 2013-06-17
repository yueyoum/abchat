# -*- coding: utf-8 -*-

import gevent
from gevent.queue import Queue
# from gevent.server import StreamServer

import struct

class MaiBoxMixIn(object):
    def __init__(self):
        self.inbox = Queue()

    def put(self, message):
        self.inbox.put(message)


class SocketMixIn(object):
    def __init__(self):
        self.head_t = struct.Struct('>i')

    def sendall(self, message):
        msg_len = len(message)
        msg_st = struct.Struct('>i%ds' % msg_len)
        x = msg_st.pack(msg_len, message)
        self.sock.sendall(x)
        print 'sendall done'


class Master(MaiBoxMixIn, gevent.Greenlet):
    def __init__(self, worker_class):
        self.workers = set()
        self.worker_class = worker_class
        MaiBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)

    def add_worker(self, w):
        print 'add worker'
        self.workers.add(w)

    def rem_worker(self, w):
        print 'remove worker'
        self.workers.remove(w)

    def handle(self, remote, address):
        self.worker_class(self, remote).start()

    def all_workers(self):
        return self.workers

    def _run(self):
        while True:
            message = self.inbox.get()
            print 'master inbox receive', message
            for w in self.all_workers():
                w.put(message)
        
        
class Worker(MaiBoxMixIn, SocketMixIn, gevent.Greenlet):
    def __init__(self, master, sock):
        self.master = master
        self.sock = sock
        MaiBoxMixIn.__init__(self)
        SocketMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        # self.master.add_worker(self)
        self.first_receive = True
        print 'Worker start'

    def _sock_recv(self):
        while True:
            data = self.sock_recv()
            self.first_receive = False
            if not data:
                print 'connection lost'
                break
            self.receive(data, 'sock')

    def _inbox_get(self):
        while True:
            data = self.inbox.get()
            self.receive(data, 'inbox')

    def sock_recv(self):
        raise NotImplemented

    def receive(self, message, tp):
        raise NotImplemented

    def _run(self):
        recv = gevent.spawn(self._sock_recv)
        get = gevent.spawn(self._inbox_get)

        def _clear(*args):
            self.master.rem_worker(self)
            get.kill()
        recv.link(_clear)
        gevent.joinall([recv, get])
        print 'worker died...'



class MyWorker(Worker):
    def sock_recv(self):
        try:
            data = self.sock.recv(4)
            if not data:
                return None
            length = self.head_t.unpack(data)
            length = length[0]
            data = self.sock.recv(length)
        except Exception as e:
            print e
            return None
        print 'worker recv', data
        return data

    def receive(self, message, tp):
        if tp == 'sock':
            self.master.put(message)
        elif tp == 'inbox':
            self.sendall(message)


# master = Master(MyWorker)
# master.start()
# print 'start server...'
# s = StreamServer(('0.0.0.0', 9090), master.handle)
# s.serve_forever()
