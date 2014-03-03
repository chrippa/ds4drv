import argparse
import os
import sys

from functools import partial
from threading import Thread

from . import __version__
from .actions import (ActionLED,
                      ReportActionBattery,
                      ReportActionBinding,
                      ReportActionBluetoothSignal,
                      ReportActionDump,
                      ReportActionInput,
                      ReportActionStatus)
from .backends import BluetoothBackend, HidrawBackend
from .config import Config
from .daemon import Daemon
from .eventloop import EventLoop
from .exceptions import BackendError
from .uinput import parse_uinput_mapping
from .utils import parse_button_combo


ACTIONS = (ActionLED,
           ReportActionBattery,
           ReportActionBinding,
           ReportActionBluetoothSignal,
           ReportActionDump,
           ReportActionInput,
           ReportActionStatus)
CONFIG_FILES = ("~/.config/ds4drv.conf", "/etc/ds4drv.conf")
DAEMON_LOG_FILE = "~/.cache/ds4drv.log"
DAEMON_PID_FILE = "/tmp/ds4drv.pid"


class DS4Controller(object):
    def __init__(self, index, options, dynamic=False):
        self.index = index
        self.dynamic = dynamic
        self.logger = Daemon.logger.new_module("controller {0}".format(index))

        self.error = None
        self.device = None
        self.loop = EventLoop()

        self.actions = [cls(self) for cls in ACTIONS]
        self.bindings = options.parent.bindings
        self.current_profile = "default"
        self.default_profile = options
        self.options = self.default_profile
        self.profiles = options.profiles
        self.profile_options = dict(options.parent.profiles)
        self.profile_options["default"] = self.default_profile

        if self.profiles:
            self.profiles.append("default")

        self.load_options(self.options)

    def fire_event(self, event, *args):
        self.loop.fire_event(event, *args)

    def load_profile(self, profile):
        if profile == self.current_profile:
            return

        profile_options = self.profile_options.get(profile)
        if profile_options:
            self.logger.info("Switching to profile: {0}", profile)
            self.load_options(profile_options)
            self.current_profile = profile
            self.fire_event("load-profile", profile)
        else:
            self.logger.warning("Ignoring invalid profile: {0}", profile)

    def next_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) + 1
        if next_index >= len(self.profiles):
            next_index = 0

        self.load_profile(self.profiles[next_index])

    def prev_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) - 1
        if next_index < 0:
            next_index = len(self.profiles) - 1

        self.load_profile(self.profiles[next_index])

    def setup_device(self, device):
        self.logger.info("Connected to {0}", device.name)

        self.device = device
        self.device.set_led(*self.options.led)
        self.fire_event("device-setup", device)
        self.loop.add_watcher(device.report_fd, self.read_report)
        self.load_options(self.options)

    def cleanup_device(self):
        self.logger.info("Disconnected")
        self.fire_event("device-cleanup")
        self.loop.remove_watcher(self.device.report_fd)
        self.device.close()
        self.device = None

        if self.dynamic:
            self.loop.stop()

    def load_options(self, options):
        self.fire_event("load-options", options)
        self.options = options

    def read_report(self):
        report = self.device.read_report()

        if not report:
            if report is False:
                return

            self.cleanup_device()
            return

        self.fire_event("device-report", report)

    def run(self):
        self.loop.run()

    def exit(self, *args):
        if self.device:
            self.cleanup_device()

        self.logger.error(*args)
        self.error = True


class ControllerAction(argparse.Action):
    # These options are moved from the normal options namespace to
    # a controller specific namespace on --next-controller.
    __options__ = ["battery_flash",
                   "bindings",
                   "dump_reports",
                   "emulate_xboxdrv",
                   "emulate_xpad",
                   "emulate_xpad_wireless",
                   "ignored_buttons",
                   "led",
                   "mapping",
                   "profile_toggle",
                   "profiles",
                   "trackpad_mouse"]

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


def stringlist(s):
    return list(filter(None, map(str.strip, s.split(","))))


def buttoncombo(sep):
    func = partial(parse_button_combo, sep=sep)
    func.__name__ = "button combo"
    return func


parser = argparse.ArgumentParser(prog="ds4drv")
parser.add_argument("--version", action="version",
                    version="%(prog)s {0}".format(__version__))

configopt = parser.add_argument_group("configuration options")
configopt.add_argument("--config", metavar="filename",
                       type=os.path.expanduser,
                       help="configuration file to read settings from. "
                            "Default is ~/.config/ds4drv.conf or "
                            "/etc/ds4drv.conf, whichever is found first")

backendopt = parser.add_argument_group("backend options")
backendopt.add_argument("--hidraw", action="store_true",
                        help="use hidraw devices. This can be used to access "
                             "USB and paired bluetooth devices. Note: "
                             "Bluetooth devices does currently not support "
                             "any LED functionality")

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
controllopt.add_argument("--ignored-buttons", metavar="button(s)",
                         type=buttoncombo(","), default=[],
                         help="a comma-separated list of buttons to never send "
                              "as joystick events. For example specify 'PS' to "
                              "disable Steam's big picture mode shortcut when "
                              "using the --emulate-* options")
controllopt.add_argument("--led", metavar="color", default="0000ff",
                         type=hexcolor,
                         help="sets color of the LED. Uses hex color codes, "
                              "e.g. 'ff0000' is red. Default is '0000ff' (blue)")
controllopt.add_argument("--bindings", metavar="bindings",
                         help="use custom action bindings specified in the "
                              "config file")
controllopt.add_argument("--mapping", metavar="mapping",
                         help="use a custom button mapping specified in the "
                              "config file")
controllopt.add_argument("--profile-toggle", metavar="button(s)",
                         type=buttoncombo("+"),
                         help="a button combo that will trigger profile "
                              "cycling, e.g. 'R1+L1+PS'")
controllopt.add_argument("--profiles", metavar="profiles",
                         type=stringlist,
                         help="profiles to cycle through using the button "
                              "specified by --profile-toggle, e.g. "
                              "'profile1,profile2'")
controllopt.add_argument("--trackpad-mouse", action="store_true",
                         help="makes the trackpad control the mouse")
controllopt.add_argument("--dump-reports", action="store_true",
                         help="prints controller input reports")
controllopt.add_argument("--next-controller", nargs=0, action=ControllerAction,
                         help="creates another controller")


def merge_options(src, dst, defaults):
    for key, value in src.__dict__.items():
        if key == "controllers":
            continue

        default = getattr(defaults, key)

        if getattr(dst, key) == default and value != default:
            setattr(dst, key, value)


def load_options():
    options = parser.parse_args(sys.argv[1:] + ["--next-controller"])

    config = Config()
    config_paths = options.config and (options.config,) or CONFIG_FILES
    for path in filter(os.path.exists, map(os.path.expanduser, config_paths)):
        config.load(path)
        break

    config_args = config.section_to_args("ds4drv") + config.controllers()
    config_options = parser.parse_args(config_args)

    defaults, remaining_args = parser.parse_known_args(["--next-controller"])
    merge_options(config_options, options, defaults)

    controller_defaults = ControllerAction.default_controller()
    for idx, controller in enumerate(config_options.controllers):
        try:
            org_controller = options.controllers[idx]
            merge_options(controller, org_controller, controller_defaults)
        except IndexError:
            options.controllers.append(controller)

    options.profiles = {}
    for name, section in config.sections("profile"):
        args = config.section_to_args(section)
        profile_options = parser.parse_args(args)
        profile_options.parent = options
        options.profiles[name] = profile_options

    options.bindings = {}
    options.bindings["global"] = config.section("bindings",
                                                key_type=parse_button_combo)
    for name, section in config.sections("bindings"):
        options.bindings[name] = config.section(section,
                                                key_type=parse_button_combo)

    for name, section in config.sections("mapping"):
        mapping = config.section(section)
        parse_uinput_mapping(name, mapping)

    for controller in options.controllers:
        controller.parent = options

    return options


def create_controller_thread(index, controller_options, dynamic=False):
    controller = DS4Controller(index, controller_options, dynamic=dynamic)

    thread = Thread(target=controller.run)
    thread.daemon = True
    thread.controller = controller
    thread.start()

    return thread


def main():
    try:
        options = load_options()
    except ValueError as err:
        Daemon.exit("Failed to parse options: {0}", err)

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

    threads = []
    for index, controller_options in enumerate(options.controllers):
        thread = create_controller_thread(index + 1, controller_options)
        threads.append(thread)

    for device in backend.devices:
        connected_devices = []
        for thread in threads:
            # Controller has received a fatal error, exit
            if thread.controller.error:
                sys.exit(1)

            if thread.controller.device:
                connected_devices.append(thread.controller.device.device_addr)

            # Clean up dynamic threads
            if not thread.is_alive():
                threads.remove(thread)

        if device.device_addr in connected_devices:
            backend.logger.warning("Ignoring already connected device: {0}",
                                   device.device_addr)
            continue

        for thread in filter(lambda t: not t.controller.device, threads):
            break
        else:
            controller_options = ControllerAction.default_controller()
            controller_options.parent = options
            thread = create_controller_thread(len(threads) + 1,
                                              controller_options,
                                              dynamic=True)
            threads.append(thread)

        thread.controller.setup_device(device)

if __name__ == "__main__":
    main()
