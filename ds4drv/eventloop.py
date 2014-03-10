import os

from collections import defaultdict, deque
from functools import wraps
from select import epoll, EPOLLIN

from .packages import timerfd
from .utils import iter_except


class Timer(object):
    """Simple interface around a timerfd connected to a event loop."""

    def __init__(self, loop, interval, callback):
        self.callback = callback
        self.interval = interval
        self.loop = loop
        self.timer = timerfd.create(timerfd.CLOCK_MONOTONIC)

    def start(self, *args, **kwargs):
        """Starts the timer.

        If the callback returns True the timer will be restarted.
        """

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
        """Stops the timer if it's running."""
        self.loop.remove_watcher(self.timer)


class EventLoop(object):
    """Basic IO, event and timer loop with callbacks."""

    def __init__(self):
        self.stop()

    def create_timer(self, interval, callback):
        """Creates a timer."""

        return Timer(self, interval, callback)

    def add_watcher(self, fd, callback):
        """Starts watching a non-blocking fd for data."""

        if not isinstance(fd, int):
            fd = fd.fileno()

        self.callbacks[fd] = callback
        self.epoll.register(fd, EPOLLIN)

    def remove_watcher(self, fd):
        """Stops watching a fd."""
        if not isinstance(fd, int):
            fd = fd.fileno()

        if fd not in self.callbacks:
            return

        self.callbacks.pop(fd, None)
        self.epoll.unregister(fd)

    def register_event(self, event, callback):
        """Registers a handler for an event."""
        self.event_callbacks[event].add(callback)

    def unregister_event(self, event, callback):
        """Unregisters a event handler."""
        self.event_callbacks[event].remove(callback)

    def fire_event(self, event, *args, **kwargs):
        """Fires a event."""
        self.event_queue.append((event, args))
        self.process_events()

    def process_events(self):
        """Processes any events in the queue."""
        for event, args in iter_except(self.event_queue.popleft, IndexError):
            for callback in self.event_callbacks[event]:
                callback(*args)

    def run(self):
        """Starts the loop."""
        self.running = True
        while self.running:
            for fd, event in self.epoll.poll():
                callback = self.callbacks.get(fd)
                if callback:
                    callback()

    def stop(self):
        """Stops the loop."""
        self.running = False
        self.callbacks = {}
        self.epoll = epoll()

        self.event_queue = deque()
        self.event_callbacks = defaultdict(set)

