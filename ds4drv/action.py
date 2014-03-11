from .config import add_controller_option
from .utils import with_metaclass

from functools import wraps

BASE_CLASSES = ["Action", "ReportAction"]


class ActionRegistry(type):
    def __init__(cls, name, bases, attrs):
        if name not in BASE_CLASSES:
            if not hasattr(ActionRegistry, "actions"):
                ActionRegistry.actions = []
            else:
                ActionRegistry.actions.append(cls)


class Action(with_metaclass(ActionRegistry)):
    """Actions are what drives most of the functionality of ds4drv."""

    @classmethod
    def add_option(self, *args, **kwargs):
        add_controller_option(*args, **kwargs)

    def __init__(self, controller):
        self.controller = controller
        self.logger = controller.logger

        self.register_event("device-setup", self.setup)
        self.register_event("device-cleanup", self.disable)
        self.register_event("load-options", self.load_options)

    def create_timer(self, interval, func):
        return self.controller.loop.create_timer(interval, func)

    def register_event(self, event, func):
        self.controller.loop.register_event(event, func)

    def unregister_event(self, event, func):
        self.controller.loop.unregister_event(event, func)

    def setup(self, device):
        pass

    def enable(self):
        pass

    def disable(self):
        pass

    def load_options(self, options):
        pass


class ReportAction(Action):
    def __init__(self, controller):
        super(ReportAction, self).__init__(controller)

        self._last_report = None
        self.register_event("device-report", self._handle_report)

    def create_timer(self, interval, callback):
        @wraps(callback)
        def wrapper(*args, **kwargs):
            if self._last_report:
                return callback(self._last_report, *args, **kwargs)
            return True

        return super(ReportAction, self).create_timer(interval, wrapper)

    def _handle_report(self, report):
        self._last_report = report
        self.handle_report(report)

    def handle_report(self, report):
        pass
