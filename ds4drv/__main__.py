import argparse
import sys

from collections import namedtuple
from threading import Thread

from . import __version__
from .actions import (ReportActionBattery, ReportActionJoystick,
                      ReportActionStatus, ReportActionCommand)
from .backends import BluetoothBackend, HidrawBackend
from .daemon import Daemon
from .exceptions import BackendError, JoystickError
from .joystick import create_joystick


DAEMON_LOG_FILE = "~/.cache/ds4drv.log"
DAEMON_PID_FILE = "/tmp/ds4drv.pid"

DS4Controller = namedtuple("DS4Controller",
                           "id joystick options dynamic logger")


class ControllerAction(argparse.Action):
    __options__ = ["battery_flash", "emulate_xboxdrv", "emulate_xpad",
                   "emulate_xpad_wireless", "led", "trackpad_mouse",
                   "no_commands"]

    @classmethod
    def default_controller(cls):
        controller = argparse.Namespace()
        defaults = parser.parse_args([])
        for option in cls.__options__:
            value = getattr(defaults, option)
            setattr(controller, option, value)

        return controller

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, "controllers"):
            setattr(namespace, "controllers", [])

        controller = argparse.Namespace()
        defaults = parser.parse_args([])
        for option in self.__options__:
            if hasattr(namespace, option):
                value = namespace.__dict__.pop(option)
                if isinstance(value, str):
                    for action in filter(lambda a: a.dest == option,
                                         parser._actions):
                        value = parser._get_value(action, value)
            else:
                value = getattr(defaults, option)

            setattr(controller, option, value)

        namespace.controllers.append(controller)


def hexcolor(color):
    color = color.strip("#")

    if len(color) != 6:
        raise ValueError

    values = (color[:2], color[2:4], color[4:6])
    values = map(lambda x: int(x, 16), values)

    return tuple(values)


parser = argparse.ArgumentParser(prog="ds4drv")
parser.add_argument("--version", action="version",
                    version="%(prog)s {0}".format(__version__))

backendopt = parser.add_argument_group("backend options")
backendopt.add_argument("--hidraw", action="store_true",
                        help="use hidraw devices. (WIP)")

daemonopt = parser.add_argument_group("daemon options")
daemonopt.add_argument("--daemon", action="store_true",
                       help="run in the background as a daemon")
daemonopt.add_argument("--daemon-log", default=DAEMON_LOG_FILE, metavar="file",
                       help="log file to create in daemon mode")
daemonopt.add_argument("--daemon-pid", default=DAEMON_PID_FILE, metavar="file",
                       help="PID file to create in daemon mode")

controllopt = parser.add_argument_group("controller options")
controllopt.add_argument("--battery-flash", action="store_true",
                         help="flashes the LED once a minute if the "
                              "battery is low")
controllopt.add_argument("--emulate-xboxdrv", action="store_true",
                         help="emulates the same joystick layout as a "
                              "Xbox 360 controller used via xboxdrv")
controllopt.add_argument("--emulate-xpad", action="store_true",
                         help="emulates the same joystick layout as a wired "
                              "Xbox 360 controller used via the xpad module")
controllopt.add_argument("--emulate-xpad-wireless", action="store_true",
                         help="emulates the same joystick layout as a wireless "
                              "Xbox 360 controller used via the xpad module")

controllopt.add_argument("--led", metavar="color", default="0000ff",
                         type=hexcolor,
                         help="sets color of the LED. Uses hex color codes, "
                              "e.g. 'ff0000' is red. Default is '0000ff' (blue)")
controllopt.add_argument("--trackpad-mouse", action="store_true",
                         help="makes the trackpad control the mouse")
controllopt.add_argument("--no-commands", action="store_true",
                         help="disables controller commands")
controllopt.add_argument("--next-controller", nargs=0, action=ControllerAction,
                         help="creates another controller")


def create_controller(index, options, dynamic=False):
    if options.emulate_xboxdrv:
        layout = "xboxdrv"
    elif options.emulate_xpad:
        layout = "xpad"
    elif options.emulate_xpad_wireless:
        layout = "xpad_wireless"
    else:
        layout = "ds4"

    try:
        joystick = create_joystick(layout, mouse=options.trackpad_mouse)
    except JoystickError as err:
        Daemon.exit("Failed to create joystick device: {0}", err)

    logger = Daemon.logger.new_module("controller {0}".format(index))
    controller = DS4Controller(index, joystick, options, dynamic, logger)
    controller.logger.info("Created devices {0} (joystick) {1} (evdev)",
                           joystick.jsdev, joystick.joystick.device.fn)

    return controller


def read_device(device, controller):
    device.set_led(*controller.options.led)

    actions = [cls(device, controller) for cls in
               (ReportActionJoystick, ReportActionStatus)]

    if controller.options.battery_flash:
        actions.append(ReportActionBattery(device, controller))

    if not controller.options.no_commands:
        actions.append(ReportActionCommand(device, controller))

    for report in device.reports:
        for action in actions:
            action.handle_report(report)

    controller.logger.info("Disconnected")
    device.close()


def main():
    options = parser.parse_args(sys.argv[1:] + ["--next-controller"])

    if options.hidraw:
        backend = HidrawBackend(Daemon.logger)
    else:
        backend = BluetoothBackend(Daemon.logger)

    try:
        backend.setup()
    except BackendError as err:
        Daemon.exit(err)

    if options.daemon:
        Daemon.fork(options.daemon_log, options.daemon_pid)

    controllers = []
    threads = []

    for index, options in enumerate(options.controllers):
        controller = create_controller(index + 1, options)
        controllers.append(controller)

    for device in backend.devices:
        for thread in threads:
            # Reclaim the joystick device if the controller is gone
            if not thread.is_alive():
                if not thread.controller.dynamic:
                    controllers.insert(0, thread.controller)
                threads.remove(thread)

        # No pre-configured controller available,
        # create one with default settings
        if not controllers:
            index = len(threads) + 1
            options = ControllerAction.default_controller()
            controller = create_controller(index, options, dynamic=True)
        else:
            controller = controllers.pop(0)

        controller.logger.info("Connected to {0}", device.name)

        thread = Thread(target=read_device, args=(device, controller))
        thread.daemon = True
        thread.controller = controller
        thread.start()
        threads.append(thread)

if __name__ == "__main__":
    main()
