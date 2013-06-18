# -*- coding: utf-8 -*-

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
