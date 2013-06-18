# -*- coding: utf-8 -*-

import struct
from gevent.queue import Queue

class MailBoxMixIn(object):
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
