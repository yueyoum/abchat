import gevent
from gevent import socket
from gevent.pool import Pool
import random
import struct

pool = Pool(500)
head_fmt = struct.Struct('>i')

def client(cid):
    s = socket.create_connection(('127.0.0.1', 7890))

    def send():
        times = 0
        while times < 100:
            times += 1
            gevent.sleep(1)
            nums = str(random.randint(10, 10000))
            data = '%s, from client %d' % ( nums, cid )
            data_len = len(data)
            fmt = struct.Struct('>i%ds'%data_len)
            data = fmt.pack(data_len, data)
            s.sendall(data)
            print 'client', cid, 'send:', nums

    def recv():
        while True:
            data = s.recv(4)
            data = head_fmt.unpack(data)
            length = data[0]
            data = s.recv(length)
            print 'client', cid, 'recive:', data

    send_job = gevent.spawn_later(1, send)
    recv_job = gevent.spawn(recv)

    def clear(*args):
        gevent.killall([send_job, recv_job])
        s.close()

    send_job.link(clear)
    recv_job.link(clear)
    gevent.joinall([send_job, recv_job])
    print 'client', cid, 'finish'


clients = pool.imap(client, xrange(1000))
gevent.spawn_later(60, lambda: clients.kill()).start()
clients.start()
gevent.run()

