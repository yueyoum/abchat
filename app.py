# -*- coding: utf-8 -*-

from base import Master, MyWorker
from gevent.server import StreamServer

from chat2_pb2 import ChatMsg, ChatInitializeResponse

import redis
r = redis.Redis(port=6381)

import sys
sys.path.append("/home/li.yu/mhxj_ios/server/lib/msg")
from player_session_pb2 import PlayerSession

class ChatMaster(Master):
    def __init__(self, worker_class):
        super(ChatMaster, self).__init__(worker_class)
        self.workers = {}

    def add_worker(self, uid, w):
        print 'add_worker'
        self.workers[uid] = w

    def rem_worker(self, uid):
        print 'rem_worker'
        print self.workers
        print uid
        del self.workers[uid]

    def _run(self):
        while True:
            message = self.inbox.get()
            msg = ChatMsg()
            msg.ParseFromString(message)
            # if msg.channel == 1:
            #     # 私聊
            #     print 'MASTER, send message to', msg.who.uid
            #     self.workers[msg.who.uid].put(message)
            # else:
            #     print 'MASTER, send message to', 'all'
            #     for w in self.workers.values():
            #         w.put(message)
            for w in self.workers.values():
                w.put(message)


class ChatWorker(MyWorker):
    def __init__(self, *args, **kwargs):
        super(ChatWorker, self).__init__(*args, **kwargs)
        self.uid = None

    @property
    def sign(self):
        return self.uid

    def sock_recv(self):
        data = super(ChatWorker, self).sock_recv()
        if self.first_receive:
            msg = PlayerSession()
            msg.ParseFromString(data)
            # 验证playersession
            self.master.add_worker(msg.uid, self)
            self.uid = msg.uid

            x = ChatInitializeResponse()
            x.ret = 0
            self.sendall(x.SerializeToString())


            data = ChatMsg()
            data.channel = 0
            data.who.uid = msg.uid
            print 'uid =', msg.uid
            cid = r.get('u.{0}.oc'.format(msg.uid))
            name, gender = r.hmget('c.{0}'.format(cid), 'name', 'gender')
            data.who.name = name.decode('utf-8')
            data.who.gender = int(gender)
            data.text = u'我来了'
            return data.SerializeToString()
        return data

    def receive(self, message, tp):
        if tp == 'sock':
            self.master.put(message)
        elif tp == 'inbox':
            self.sendall(message)


master = ChatMaster(ChatWorker)
master.start()
print 'start server...'
s = StreamServer(('0.0.0.0', 5678), master.handle)
s.serve_forever()
