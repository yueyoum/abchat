# -*- coding: utf-8 -*-

import logging
try:
    from logging import NullHandler
except ImportError:
    # Python version < 2.7
    class NullHandler(logging.Handler):
        def handler(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None


__all__ = ['log',]

log = logging.getLogger('abchat')
log.setLevel(logging.DEBUG)
log.addHandler(NullHandler())
