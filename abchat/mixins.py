# -*- coding: utf-8 -*-

import struct
import ctypes
from gevent.queue import Queue

from .log import log

class MailBoxMixIn(object):
    def __init__(self):
        self.inbox = Queue()

    def put(self, message):
        self.inbox.put(message)


class StreamSocketMixIn(object):
    def __init__(self, pre_malloc_size=None):
        self.head_t = struct.Struct('>i')
        if pre_malloc_size:
            self.buf = ctypes.create_string_buffer(pre_malloc_size)
        else:
            self.buf = None

    def sendall(self, message):
        msg_len = len(message)
        fmt = '>i%ds' % msg_len
        msg_st = struct.Struct(fmt)
        if self.buf:
            msg_size = struct.calcsize(fmt)
            try:
                msg_st.pack_into(self.buf, 0, msg_len, message)
                x = self.buf.raw[:msg_size]
                ctypes.memset(self.buf, 0, msg_size)
            except struct.error:
                log.error("pack_into error, this worker never use pack_into again")
                self.buf = None
                x = msg_st.pack(msg_len, message)
        else:
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
