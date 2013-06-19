import gevent
from gevent import socket
import random

def client(cid):
    s = socket.create_connection(('127.0.0.1', 7890))
    w = s.makefile('w')
    r = s.makefile('r')
    while True:
        gevent.sleep(random.randint(1, 10)/10.0)
        w.write('%s, from client %d\n' % (str(random.randint(10, 100000)), cid))
        w.flush()
        line = r.readline()
        print 'client', cid, 'recive:', line,

    s.close()


clients = [gevent.spawn(client, cid) for cid in range(1, 100)]


def quit():
    gevent.killall(clients)

q = gevent.spawn_later(60, quit)
q.start()

gevent.joinall(clients)

