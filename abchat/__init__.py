# -*- coding: utf-8 -*-

from .mixins import StreamSocketMixIn, LineSocketMixIn
from .core import Master, BaseWorker, ContinueFlag

class StreamWorker(StreamSocketMixIn, BaseWorker):
    def __init__(self, *args, **kwargs):
        pre_malloc_size = kwargs.pop('pre_malloc_size', None)
        StreamSocketMixIn.__init__(self, pre_malloc_size=pre_malloc_size)
        BaseWorker.__init__(self, *args, **kwargs)


class LineWorker(LineSocketMixIn, BaseWorker):
    def __init__(self, *args, **kwargs):
        BaseWorker.__init__(self, *args, **kwargs)
        self.rfile = self.sock.makefile('rb')
        self.wfile = self.sock.makefile('wb')
