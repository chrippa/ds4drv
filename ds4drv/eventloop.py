import os
import ctypes

from collections import defaultdict, deque
from functools import wraps
from select import epoll, EPOLLIN
from struct import Struct

from .packages import timerfd
from .utils import iter_except


class eventfd(object):
    """Simple wrapper around the eventfd syscall."""

    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    struct = Struct("Q")

    def __init__(self, value=0, flags=0):
        self.fd = self.libc.eventfd(value, flags)

    def fileno(self):
        return self.fd

    def write(self, value):
        buf = self.struct.pack(value)
        os.write(self.fd, buf)

    def read(self):
        buf = os.read(self.fd, 8)
        return self.struct.unpack(buf)[0]


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

    def fire_event(self, event, *args):
        self.event_queue.append((event, args))
        self.event_fd.write(1)

    def process_events(self):
        for event, args in iter_except(self.event_queue.popleft, IndexError):
            for callback in self.event_callbacks[event]:
                callback(*args)

        self.event_fd.read()

    def run(self):
        self.add_watcher(self.event_fd, self.process_events)
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

        self.event_fd = eventfd()
        self.event_queue = deque()
        self.event_callbacks = defaultdict(set)

