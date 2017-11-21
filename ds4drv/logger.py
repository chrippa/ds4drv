import sys

from threading import Lock


LEVELS = ["none", "error", "warning", "info"]
FORMAT = "[{level}][{module}] {msg}\n"


class Logger(object):
    def __init__(self):
        self.output = sys.stdout
        self.level = 0
        self.lock = Lock()

    def new_module(self, module):
        return LoggerModule(self, module)

    def set_level(self, level):
        try:
            index = LEVELS.index(level)
        except ValueError:
            return

        self.level = index

    def set_output(self, output):
        self.output = output

    def msg(self, module, level, msg, *args, **kwargs):
        if self.level < level or level > len(LEVELS):
            return

        msg = str(msg).format(*args, **kwargs)

        with self.lock:
            self.output.write(FORMAT.format(module=module,
                                            level=LEVELS[level],
                                            msg=msg))
            if hasattr(self.output, "flush"):
                self.output.flush()


class LoggerModule(object):
    def __init__(self, manager, module):
        self.manager = manager
        self.module = module

    def error(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 1, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 2, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 3, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.manager.msg(self.module, 4, msg, *args, **kwargs)
