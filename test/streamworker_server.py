from gevent.server import StreamServer
from server_init import log

from abchat import Master, StreamWorker


class MyWorker(StreamWorker):
    def sock_recv(self):
        data = super(MyWorker, self).sock_recv()
        if data:
            if self.first_receive:
                # adding self to Master's workers
                self.master.workers.add(self)
                self.first_receive = False
        return data

    def before_worker_exit(self, *args):
        self.master.workers.rem(self)

Master.set_worker_kwargs(pre_malloc_size=1024)
master = Master(MyWorker)
master.start()

log.debug('start...')
s = StreamServer(('0.0.0.0', 7890), master.handle)
s.serve_forever()
