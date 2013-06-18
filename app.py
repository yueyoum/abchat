# -*- coding: utf-8 -*-
from gevent.monkey import patch_all
patch_all()

import os
import sys

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SERVER_PATH = os.path.dirname(CURRENT_PATH)
MSG_PATH = os.path.join(SERVER_PATH, 'lib', 'msg')
sys.path.append(MSG_PATH)

import redis
from gevent.server import StreamServer

from base import Master, StreamWorker, WorkersContainerDictType, MasterInterfaceRedis
from chat2_pb2 import ChatMsg, ChatInitializeResponse
from player_session_pb2 import PlayerSession

r = redis.Redis(port=6381)

class ChatMaster(Master):
    def emit_message(self, message):
        msg = ChatMsg()
        msg.ParseFromString(message)
        if msg.channel == 1:
            # 私聊
            print 'MASTER, send message to', msg.to.uid
            try:
                remote = self.workers.workers[msg.to.uid]
            except KeyError:
                print 'remote has gone away...'
                return
            remote.put(message)
        else:
            print 'MASTER, send message to', 'all'
            for w in self.workers.all_workers():
                w.put(message)


class ChatWorker(StreamWorker):
    def sock_recv(self):
        data = super(ChatWorker, self).sock_recv()
        if not data:
            return data

        if self.first_receive:
            msg = PlayerSession()
            msg.ParseFromString(data)
            # 验证playersession
            self.uid = msg.uid
            cid = r.get('u.{0}.oc'.format(self.uid))
            name, gender = r.hmget('c.{0}'.format(cid), 'name', 'gender')
            self.name = name.decode('utf-8')
            self.gender = int(gender)
            self.master.workers.add(msg.uid, self)

            # 取私聊信息
            msg = ChatInitializeResponse()
            msg.ret = 0
            self.sendall(msg.SerializeToString())
            return

        msg = ChatMsg()
        msg.ParseFromString(data)
        msg.who.uid = self.uid
        msg.who.name = self.name
        msg.who.gender = self.gender

        data = msg.SerializeToString()
        if msg.channel == 1:
            # 私聊，填充to
            cid = r.get('u.{0}.oc'.format(msg.to.uid))
            name, gender = r.hmget('c.{0}'.format(cid), 'name', 'gender')
            msg.to.name = name.decode('utf-8')
            msg.to.gender = int(gender)
            self.sendall(msg.SerializeToString())

        return data

    def _clear(self, *args):
        # 可能在 解 PlayerSession的时候就报错了，这样self就没有uid
        uid = getattr(self, 'uid', None)
        if uid:
            self.master.workers.rem(self.uid)




master = ChatMaster(ChatWorker, WorkersContainerDictType)
master.start()

interface = MasterInterfaceRedis(r, 'chatbc', master)
interface.start()

print 'start server...'
s = StreamServer(('0.0.0.0', 5678), master.handle)
s.serve_forever()
