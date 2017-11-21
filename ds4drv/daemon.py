import atexit
import os
import sys

from signal import signal, SIGTERM

from .logger import Logger


class Daemon(object):
    logger = Logger()
    logger.set_level("info")
    logger_module = logger.new_module("daemon")

    @classmethod
    def fork(cls, logfile, pidfile):
        if os.path.exists(pidfile):
            cls.exit("ds4drv appears to already be running. Kill it "
                     "or remove {0} if it's not really running.", pidfile)

        cls.logger_module.info("Forking into background, writing log to {0}",
                               logfile)

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
            output = open(logfile, "w")
        except OSError as err:
            cls.exit("Failed to open log file: {0} ({1})", logfile, err)

        cls.logger.set_output(output)

    @classmethod
    def exit(cls, *args, **kwargs):
        cls.logger_module.error(*args, **kwargs)
        sys.exit(1)
