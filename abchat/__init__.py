# -*- coding: utf-8 -*-

from .mixins import StreamSocketMixIn, LineSocketMixIn
from .core import Master, BaseWorker, InvalidData

class StreamWorker(StreamSocketMixIn, BaseWorker):
    def __init__(self, *args, **kwargs):
        StreamSocketMixIn.__init__(self)
        BaseWorker.__init__(self, *args, **kwargs)


class LineWorker(LineSocketMixIn, BaseWorker):
    def __init__(self, *args, **kwargs):
        self.rfile = self.sock.makefile('rb')
        self.wfile = self.sock.makefile('wb')
        BaseWorker.__init__(self, *args, **kwargs)
