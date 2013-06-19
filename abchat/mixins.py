# -*- coding: utf-8 -*-

import struct
from gevent.queue import Queue

from .log import log

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

    def sock_recv(self):
        try:
            data = self.sock.recv(4)
            if not data:
                return None
            length = self.head_t.unpack(data)
            length = length[0]
            data = self.sock.recv(length)
        except Exception as e:
            log.error('StreamSocketMixIn, sock_recv error: {0}'.format(str(e)))
            return None
        return data

class LineSocketMixIn(object):
    def sendall(self, message):
        if not message.endswith('\n'):
            message = '%s\n' % message
        self.wfile.write(message)
        self.wfile.flush()

    def sock_recv(self):
        try:
            return self.rfile.readline()
        except Exception as e:
            log.error('LineSocketMixIn, sock_recv error: {0}'.format(str(e)))
            return ''