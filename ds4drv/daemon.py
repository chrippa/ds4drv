import atexit
import os
import sys

from threading import Lock
from signal import signal, SIGTERM


CONTROLLER_LOG = "Controller {0}"
BLUETOOTH_LOG = "Bluetooth"


class Daemon(object):
    lock = Lock()
    output = sys.stdout

    @classmethod
    def fork(cls, logfile, pidfile):
        if os.path.exists(pidfile):
            cls.exit("ds4drv appears to already be running. Kill it "
                     "or remove {0} if it's not really running.", pidfile)

        cls.info("Forking into background, writing log to {0}", logfile)

        try:
            pid = os.fork()
        except OSError as err:
            cls.exit("Failed to fork: {0}", err)

        if pid == 0:
            os.setsid()

            try:
                pid = os.fork()
            except OSError as err:
                cls.exit("Failed to fork child process: {0}", err)

            if pid == 0:
                os.chdir("/")
                cls.open_log(logfile)
            else:
                sys.exit(0)
        else:
            sys.exit(0)

        cls.create_pid(pidfile)

    @classmethod
    def create_pid(cls, pidfile):
        @atexit.register
        def remove_pid():
            if os.path.exists(pidfile):
                os.remove(pidfile)

        signal(SIGTERM, lambda *a: sys.exit())

        try:
            with open(pidfile, "w") as fd:
                fd.write(str(os.getpid()))
        except OSError:
            pass

    @classmethod
    def open_log(cls, logfile):
        logfile = os.path.expanduser(logfile)
        dirname = os.path.dirname(logfile)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError as err:
                cls.exit("Failed to open log file: {0} ({1})", logfile, err)

        try:
            cls.output = open(logfile, "w")
        except OSError as err:
            cls.exit("Failed to open log file: {0} ({1})", logfile, err)

    @classmethod
    def msg(cls, prefix, fmt, *args, **kwargs):
        subprefix = kwargs.pop("subprefix", None)

        if subprefix:
            msg = "[{0}][{1}] ".format(prefix, subprefix)
        else:
            msg = "[{0}] ".format(prefix)

        msg += fmt.format(*args, **kwargs)

        with cls.lock:
            cls.output.write(msg + "\n")
            cls.output.flush()

    @classmethod
    def info(cls, *args, **kwargs):
        cls.msg("info", *args, **kwargs)

    @classmethod
    def warn(cls, *args, **kwargs):
        cls.msg("warning", *args, **kwargs)

    @classmethod
    def exit(cls, *args, **kwargs):
        cls.msg("error", *args, **kwargs)
        sys.exit(1)
