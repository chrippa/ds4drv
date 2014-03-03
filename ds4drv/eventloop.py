import os

from collections import defaultdict, deque
from functools import wraps
from select import epoll, EPOLLIN

from .packages import timerfd
from .utils import iter_except


class EventLoop(object):
    """Basic IO, event and timer loop with callbacks."""

    def __init__(self):
        self.stop()

    def add_timer(self, interval, func):
        fd = timerfd.create(timerfd.CLOCK_MONOTONIC)
        timerfd.settime(fd, 0, timerfd.itimerspec(interval, interval))

        @wraps(func)
        def callback():
            os.read(fd, 8)
            repeat = func()
            if not repeat:
                self.remove_watcher(fd)

        self.add_watcher(fd, callback)

    def remove_timer(self, func):
        for fd, callback in dict(self.callbacks).items():
            if callback == func:
                self.remove_watcher(fd)

            if hasattr(callback, "__wrapped__"):
                callback = callback.__wrapped__
                if callback == func:
                    self.remove_watcher(fd)

    def add_watcher(self, fd, callback):
        if not isinstance(fd, int):
            fd = fd.fileno()

        self.callbacks[fd] = callback
        self.epoll.register(fd, EPOLLIN)

    def remove_watcher(self, fd):
        if not isinstance(fd, int):
            fd = fd.fileno()

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

