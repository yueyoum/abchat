# -*- coding: utf-8 -*-

# 需要patch  redis-py
import gevent.monkey
gevent.monkey.patch_all()

import os
import sys
import time
import logging
from logging import handlers
import daemonized

import redis
from gevent.server import StreamServer

from abchat import Master, StreamWorker, ContinueFlag
from abchat.container import WorkersContainerDictType
from abchat.interface import MasterInterfaceRedis

from chat2_pb2 import ChatMsg, ChatInitializeResponse

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SERVER_PATH = os.path.dirname(CURRENT_PATH)
WEB_PATH = os.path.join(SERVER_PATH, 'web')
TMP_PATH = os.path.join(SERVER_PATH, 'tmp')
sys.path.insert(0, WEB_PATH)
sys.path.insert(0, SERVER_PATH)

from settings import REDIS_HOST, REDIS_PORT, CHAT_PORT
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

log = logging.getLogger('abchat')
# handle = logging.StreamHandler()
handle = handlers.TimedRotatingFileHandler(os.path.join(TMP_PATH, 'chat.log'), when='W6')
handle.setLevel(logging.DEBUG)
handle.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
log.addHandler(handle)


# 玩家不在线的时候，保存多少条私聊信息
PRIVATE_MSG_LIMIT = 20


class ChatMaster(Master):
    def emit_message(self, message):
        msg = ChatMsg()
        msg.ParseFromString(message)
        if msg.channel == 1:
            # 私聊
            try:
                remote = self.workers.workers[msg.to.uid]
            except KeyError:
                log.error("{0} has gone away...".format(msg.to.uid))
                # 保存个人的私聊
                self.save_private_msg(msg.to.uid, message)
                return
            remote.put(message)
        else:
            # 世界频道
            self.broadcast_message(message)

    def save_private_msg(self, uid, msg):
        key = rediskey.user_chat_msgs(uid)
        length = r.rpush(key, msg)
        if length > PRIVATE_MSG_LIMIT:
            r.lpop(key)


class ChatWorker(StreamWorker):
    def sock_recv(self):
        data = super(ChatWorker, self).sock_recv()
        if not data:
            return data

        if self.first_receive:
            self.first_receive = False
            msg = PlayerSession()
            try:
                msg.ParseFromString(data)
            except:
                # 首次连接，可能是flash在请求安全认证
                self.sock.sendall(xml)
                return ContinueFlag

            # 验证playersession
            if not verify_game_session(msg.uid, msg.session):
                # 断开连接
                return None

            self.uid = msg.uid
            cid = r.get(rediskey.user_own_char(self.uid))
            name, gender = r.hmget(rediskey.char(cid), 'name', 'gender')
            self.name = name.decode('utf-8')
            self.gender = int(gender)
            # 将自身添加入master的workers中
            self.master.workers.add(msg.uid, self)

            msg = ChatInitializeResponse()
            msg.ret = 0
            # 取私聊信息
            private_msgs = r.lrange(rediskey.user_chat_msgs(self.uid), 0, -1)
            for pm in private_msgs:
                cm = msg.msgs.add()
                cm.MergeFromString(pm)
            r.delete(rediskey.user_chat_msgs(self.uid))
            self.sendall(msg.SerializeToString())
            return ContinueFlag

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
            log.debug("{0} from {1}, to {2}: {3}".format(self.address, msg.who.uid, msg.to.uid, msg.text.encode('utf-8')))
            cid = r.get(rediskey.user_own_char(msg.to.uid))
            if not cid:
                # 没找到这个人
                log.error("{0}, {1} chat to {2}, But can not find {2}".format(self.address, self.uid, msg.to.uid))
                return None
            name, gender = r.hmget(rediskey.char(cid), 'name', 'gender')
            msg.to.name = name.decode('utf-8')
            msg.to.gender = int(gender)
            # 将消息发回去
            self.sendall(msg.SerializeToString())
        else:
            # 世界频道，限制发送速度
            timestamp = getattr(self, 'timestamp', None)
            self.timestamp = time.time()
            if timestamp:
                if self.timestamp - timestamp < 3:
                    log.debug('{0} {1} speak too fast, ignore'.format(self.address, msg.who.uid))
                    return ContinueFlag
            log.debug("{0} from {1}, to all: {2}".format(self.address, msg.who.uid, msg.text.encode('utf-8')))

        return data

    def before_worker_exit(self):
        # 可能在 解 PlayerSession的时候就报错了，这样self就没有uid
        uid = getattr(self, 'uid', None)
        if uid:
            self.master.workers.rem(self.uid)


def start_server(port=5678):
    ChatMaster.set_worker_kwargs(pre_malloc_size=1024)
    master = ChatMaster(ChatWorker, WorkersContainerDictType, dump_status_interval=600)
    master.start()

    interface = MasterInterfaceRedis(r, 'chatbc', master)
    interface.start()

    log.debug('start server...')
    s = StreamServer(('0.0.0.0', port), master.handle)
    s.serve_forever()

if __name__ == '__main__':
    @daemonized.Daemonize()
    def daemon_server():
        start_server(port=CHAT_PORT)

    daemon_server()
