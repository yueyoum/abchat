# -*- coding: utf-8 -*-

from .log import log

class WorkersContainerListType(object):
    def __init__(self):
        self.workers = set()

    def add(self, w):
        self.workers.add(w)

    def rem(self, w):
        self.workers.remove(w)

    def all_workers(self):
        return self.workers

    def amount(self):
        return len(self.workers)


class WorkersContainerDictType(object):
    def __init__(self):
        self.workers = {}
        self._all_workers = set()

    def add(self, key, w):
        if key in self.workers:
            self._all_workers.remove(self.workers[key])
        self.workers[key] = w
        self._all_workers.add(w)

    def rem(self, key):
        try:
            self._all_workers.remove(self.workers[key])
            del self.workers[key]
        except KeyError:
            log.error('WorkersContainerDictType, rem worker, KeyError, key={0}'.format(key))

    def all_workers(self):
        return self._all_workers

    def amount(self):
        return len(self.workers)
