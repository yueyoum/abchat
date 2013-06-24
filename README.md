# ABChat

Abstract Chat Server Based on Gevent

## Benchmark

*   CPU: AMD Athlon(tm) II X2 240 Processor
*   OS: 2.6.31-gentoo-r10 i686
*   MemTotal: 901900 kB


run test server and test client at the same machine,
server can handler 1,000 connected clients send message to each other every second.

which means, every second, server receive 1,000 messages, and send every message to 1,000 clients.


# GuideLine

```python
# if using some block library
# try monkey patch first
import gevent.monkey
gevent.monkey.patch_all()

from gevent.server import StreamServer

from abchat import Master, StreamWorker, ContinueFlag
form abchat.container import WorkersContainerDictType


class MyMaster(Master):
    def emit_message(self, message):
        """When any clients receive message,
        This method will be called in a spawned greenlet
        """

        # parse your message, and handle it like this:
        if private message:
            try:
                remote = self.workers.workers[TARGET]
            except KeyError:
                do whatever you want
            remote.put(message)
        else broadcase message to all clients:
            self.broadcase_message(message)


class MyWorker(StreamWorker):
    def sock_recv(self):
        """Return None will close the connection,
        Return ContinueFlag will ignore this message,
        and go on receive the coming message.
        """
        message = super(MyWorker, self).sock_recv() # always do this
        if not message:
            return message

        if self.first_receive:
            self.first_receive = False
            # You should do some Authenticate here
            # like this:
            if authorized:
            #     at here, you should add this worker in master's container
                self.master.wokers.add(SIGN, self) # SIGN represent this client
                return ContinueFlag
            else:
                return None

        # parse message,
        # if you wanna close the connections, return None
        # if you wanna ignore this message, return ContinueFlag
        # if you wanna limit the client send interva, do this:
        interval_result = self.check_interval()
        if interval_result is ContinueFlag:
            # too fast, ignore this message
            return ContinueFlag

        # finally, return your parsed message
        return message

    def before_worker_exit(self):
        """remove self worker from master's container"""
        self.master.wokers.rem(SIGN)

        # some addtional jobs...



def start():
    MyMaster.set_worker_kwargs(pre_malloc_size=1024, client_send_interval=10)
    # pre_malloc_size: is not None, each worker will malloc some memory,
    # used for struct.pack_into method, this can avoid malloc memory in each sendall call.
    # default is None

    # client_send_interval: used for Limit the transmission rate.
    # if value is None, means no limits.
    # you should call self.check_interval() method  in worker when you needs
    # default is None

    master = MyMaster(MyWorker, WorkersContainerDictType, dump_status_interval=600)
    # dump_status_interval: interval of log out how many clients have connected. secends

    master.start()

    s = StreamServer(('0.0.0.0', 8000), master.handle)
    s.serve_forever()

```
