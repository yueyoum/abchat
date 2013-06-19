# -*- coding: utf-8 -*-

# 需要patch  redis-py
import gevent.monkey
gevent.monkey.patch_all()

import os
import sys
import logging

import redis
from gevent.server import StreamServer

from abchat import Master, StreamWorker, InvalidData
from abchat.container import WorkersContainerDictType
from abchat.interface import MasterInterfaceRedis
from abchat.log import log

from chat2_pb2 import ChatMsg, ChatInitializeResponse

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SERVER_PATH = os.path.dirname(CURRENT_PATH)
WEB_PATH = os.path.join(SERVER_PATH, 'web')
sys.path.insert(0, WEB_PATH)
sys.path.insert(0, SERVER_PATH)

from settings import REDIS_HOST, REDIS_PORT
from lib.msg.player_session_pb2 import PlayerSession
from lib.utils import verify_game_session
import rediskey

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


xml = """<?xml version="1.0"?>
<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">
<cross-domain-policy>
  <site-control permitted-cross-domain-policies="master-only"/>
  <allow-access-from domain="*" to-ports="*"/>
</cross-domain-policy>\0"""

handle = logging.StreamHandler()
handle.setLevel(logging.NOTSET)
handle.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
log.addHandler(handle)


class ChatMaster(Master):
    def emit_message(self, message):
        msg = ChatMsg()
        msg.ParseFromString(message)
        if msg.channel == 1:
            # 私聊
            log.debug("Send message to {0}".format(msg.to.uid))
            try:
                remote = self.workers.workers[msg.to.uid]
            except KeyError:
                log.error("{0} has gone away...".format(msg.to.uid))
                # 保存个人的私聊
                return
            remote.put(message)
        else:
            log.debug("Send message to all")
            for w in self.workers.all_workers():
                w.put(message)


class ChatWorker(StreamWorker):
    def sock_recv(self):
        data = super(ChatWorker, self).sock_recv()
        if not data:
            return data

        if self.first_receive:
            msg = PlayerSession()
            try:
                msg.ParseFromString(data)
            except:
                # 首次连接，可能是flash在请求安全认证
                self.sock.sendall(xml)
                return InvalidData

            # TODO 验证playersession
            self.uid = msg.uid
            cid = r.get(rediskey.user_own_char(self.uid))
            name, gender = r.hmget(rediskey.char(cid), 'name', 'gender')
            self.name = name.decode('utf-8')
            self.gender = int(gender)
            # 将自身添加入master的workers中
            self.master.workers.add(msg.uid, self)

            # TODO 取私聊信息
            msg = ChatInitializeResponse()
            msg.ret = 0
            self.sendall(msg.SerializeToString())
            return

        msg = ChatMsg()
        try:
            msg.ParseFromString(data)
        except:
            # 断开连接
            log.error("{0} Wrong Data, ChatMsg cannot parse it".format(self.address))
            return None

        # client发送过来不用填充who，这里将其填充
        msg.who.uid = self.uid
        msg.who.name = self.name
        msg.who.gender = self.gender

        data = msg.SerializeToString()
        if msg.channel == 1:
            # 私聊，填充to
            cid = r.get(rediskey.user_own_char(msg.to.uid))
            if not cid:
                # 没找到这个人
                log.error("{0}, {1} chat to {2}, But can not find {2}".format(self.address, self.uid, msg.to.uid))
                return InvalidData
            name, gender = r.hmget(rediskey.char(cid), 'name', 'gender')
            msg.to.name = name.decode('utf-8')
            msg.to.gender = int(gender)
            # 将消息发回去
            self.sendall(msg.SerializeToString())

        return data

    def clear_worker(self, *args):
        # 可能在 解 PlayerSession的时候就报错了，这样self就没有uid
        uid = getattr(self, 'uid', None)
        if uid:
            self.master.workers.rem(self.uid)




master = ChatMaster(ChatWorker, WorkersContainerDictType)
master.start()

interface = MasterInterfaceRedis(r, 'chatbc', master)
interface.start()

log.debug('start server...')
s = StreamServer(('0.0.0.0', 5678), master.handle)
s.serve_forever()
