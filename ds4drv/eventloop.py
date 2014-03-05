import os

from collections import defaultdict, deque
from functools import wraps
from select import epoll, EPOLLIN

from .packages import timerfd
from .utils import iter_except


class Timer(object):
    def __init__(self, loop, interval, callback):
        self.callback = callback
        self.interval = interval
        self.loop = loop
        self.timer = timerfd.create(timerfd.CLOCK_MONOTONIC)

    def start(self, *args, **kwargs):
        @wraps(self.callback)
        def callback():
            os.read(self.timer, 8)
            repeat = self.callback(*args, **kwargs)
            if not repeat:
                self.stop()

        spec = timerfd.itimerspec(self.interval, self.interval)
        timerfd.settime(self.timer, 0, spec)

        self.loop.remove_watcher(self.timer)
        self.loop.add_watcher(self.timer, callback)

    def stop(self):
        self.loop.remove_watcher(self.timer)


class EventLoop(object):
    """Basic IO, event and timer loop with callbacks."""

    def __init__(self):
        self.stop()

    def create_timer(self, interval, callback):
        return Timer(self, interval, callback)

    def add_watcher(self, fd, callback):
        if not isinstance(fd, int):
            fd = fd.fileno()

        self.callbacks[fd] = callback
        self.epoll.register(fd, EPOLLIN)

    def remove_watcher(self, fd):
        if not isinstance(fd, int):
            fd = fd.fileno()

        if fd not in self.callbacks:
            return

        self.callbacks.pop(fd, None)
        self.epoll.unregister(fd)

    def register_event(self, event, callback):
        self.event_callbacks[event].add(callback)

    def unregister_event(self, event, callback):
        self.event_callbacks[event].remove(callback)

    def fire_event(self, event, *args, **kwargs):
        self.event_queue.append((event, args))
        self.process_events()

    def process_events(self):
        for event, args in iter_except(self.event_queue.popleft, IndexError):
            for callback in self.event_callbacks[event]:
                callback(*args)

    def run(self):
        self.running = True
        while self.running:
            for fd, event in self.epoll.poll():
                callback = self.callbacks.get(fd)
                if callback:
                    callback()

    def stop(self):
        self.running = False
        self.callbacks = {}
        self.epoll = epoll()

        self.event_queue = deque()
        self.event_callbacks = defaultdict(set)

