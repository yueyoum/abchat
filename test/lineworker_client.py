import gevent
from gevent import socket
from gevent.pool import Pool
import random

pool = Pool(500)

def client(cid):
    s = socket.create_connection(('127.0.0.1', 7890))
    w = s.makefile('w')
    r = s.makefile('r')

    def send():
        times = 0
        while times < 100:
            times += 1
            gevent.sleep(1)
            data = str(random.randint(10, 10000))
            w.write('%s, from client %d\n' % (data, cid))
            w.flush()
            print 'client', cid, 'send:', data

    def recv():
        while True:
            line = r.readline()
            print 'client', cid, 'recive:', line,
            if not line:
                break

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

