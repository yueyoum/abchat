import logging
from gevent.server import StreamServer

from abchat import Master, LineWorker

log = logging.getLogger('abchat')
handler = logging.StreamHandler()
handler.setLevel(logging.NOTSET)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
log.addHandler(handler)

class MyWorker(LineWorker):
    def sock_recv(self):
        data = super(MyWorker, self).sock_recv()
        if data:
            if self.first_receive:
                # adding self to Master's workers
                self.master.workers.add(self)
                self.first_receive = False
        return data

    def clear_worker(self, *args):
        self.master.workers.rem(self)

master = Master(MyWorker)
master.start()

log.debug('start...')
s = StreamServer(('0.0.0.0', 7890), master.handle)
s.serve_forever()
