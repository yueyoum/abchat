# -*- coding: utf-8 -*-
import gevent

class MasterInterface(gevent.Greenlet):
    def __init__(self, master):
        self.master = master
        gevent.Greenlet.__init__(self)

    def enter(self, *args, **kwargs):
        raise NotImplemented()

    def _run(self):
        while True:
            gevent.sleep(0)
            data = self.enter()
            self.master.put(data)


class MasterInterfaceRedis(MasterInterface):
    def __init__(self, r, key, master):
        self.r = r
        self.key = key
        super(MasterInterfaceRedis, self).__init__(master)

    def enter(self):
        _, data = self.r.blpop(self.key)
        return data
