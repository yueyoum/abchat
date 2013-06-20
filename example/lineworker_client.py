import gevent
from gevent import socket
from gevent.pool import Pool
import random

pool = Pool(1000)

def client(cid):
    s = socket.create_connection(('127.0.0.1', 7890))
    w = s.makefile('w')
    r = s.makefile('r')
    times = 0
    while times < 10:
        times += 1
        gevent.sleep(random.randint(5, 10)/10.0)
        w.write('%s, from client %d\n' % (str(random.randint(10, 100000)), cid))
        w.flush()
        line = r.readline()
        print 'client', cid, 'recive:', line,
        if not line:
            break

    s.close()


clients = pool.imap(client, xrange(2000))
gevent.spawn_later(60, lambda: clients.kill()).start()
clients.start()
gevent.run()

