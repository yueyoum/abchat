# -*- coding: utf-8 -*-
import struct

import gevent
from gevent.queue import Queue


class MaiBoxMixIn(object):
    def __init__(self):
        self.inbox = Queue()

    def put(self, message):
        self.inbox.put(message)


class StreamSocketMixIn(object):
    def __init__(self):
        self.head_t = struct.Struct('>i')

    def sendall(self, message):
        msg_len = len(message)
        msg_st = struct.Struct('>i%ds' % msg_len)
        x = msg_st.pack(msg_len, message)
        self.sock.sendall(x)
        print 'sendall done'

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
        return data

class LineSocketMixIn(object):
    def sendall(self, message):
        self.wfile.writeline(message)

    def sock_recv(self):
        return self.rfile.readline()



class WorkersContainerListType(object):
    def __init__(self):
        self.workers = set()

    def add(self, w):
        self.workers.add(w)

    def rem(self, w):
        self.workers.remove(w)

    def all_workers(self):
        return self.workers


class WorkersContainerDictType(object):
    def __init__(self):
        self.workers = {}

    def add(self, key, w):
        self.workers[key] = w

    def rem(self, key):
        try:
            del self.workers[key]
        except KeyError:
            print 'rem worker, key error'

    def all_workers(self):
        return self.workers.values()


class Master(MaiBoxMixIn, gevent.Greenlet):
    def __init__(self, worker_class, worker_container_type=WorkersContainerListType):
        self.workers = worker_container_type()
        self.worker_class = worker_class
        MaiBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)

    def handle(self, remote, address):
        self.worker_class(self, remote).start()

    def _run(self):
        while True:
            message = self.inbox.get()
            self.emit_message(message)

    def emit_message(self, message):
        for w in self.workers.all_workers():
            w.put(message)
        

class BaseWorker(MaiBoxMixIn, gevent.Greenlet):
    def __init__(self, master, sock):
        self.master = master
        self.sock = sock
        self.rfile = self.sock.makefile('rb')
        self.wfile = self.sock.makefile('wb')
        MaiBoxMixIn.__init__(self)
        gevent.Greenlet.__init__(self)
        self.first_receive = True
        print 'new worker'

    def _sock_recv(self):
        while True:
            data = self.sock_recv()
            if self.first_receive:
                self.first_receive = False
                continue

            if not data:
                print 'connection lost'
                break
            self.receive(data, 'sock')

    def _inbox_get(self):
        while True:
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


class StreamWorker(StreamSocketMixIn, BaseWorker):
    def __init__(self, *args, **kwargs):
        StreamSocketMixIn.__init__(self)
        BaseWorker.__init__(self, *args, **kwargs)

class LineWorker(LineSocketMixIn, BaseWorker):
    pass


class MasterInterface(gevent.Greenlet):
    def __init__(self, master):
        self.master = master
        gevent.Greenlet.__init__(self)

    def enter(self, *args, **kwargs):
        raise NotImplemented()

    def _run(self):
        print 'MasterInterface _run'
        while True:
            gevent.sleep(0)
            data = self.enter()
            print 'MasterInterface got data'
            self.master.put(data)


class MasterInterfaceRedis(MasterInterface):
    def __init__(self, r, key, master):
        self.r = r
        self.key = key
        super(MasterInterfaceRedis, self).__init__(master)

    def enter(self):
        _, data = self.r.blpop(self.key)
        return data
