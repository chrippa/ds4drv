import argparse
import os
import sys

from itertools import cycle
from threading import Thread

from . import __version__
from .actions import (ReportActionBattery, ReportActionBinding,
                      ReportActionInput, ReportActionStatus)
from .backends import BluetoothBackend, HidrawBackend
from .config import Config
from .daemon import Daemon
from .exceptions import BackendError, DeviceError
from .uinput import create_uinput_device, parse_uinput_mapping
from .utils import parse_button_combo as buttoncombo


CONFIG_FILES = ("~/.config/ds4drv.conf", "/etc/ds4drv.conf")
DAEMON_LOG_FILE = "~/.cache/ds4drv.log"
DAEMON_PID_FILE = "/tmp/ds4drv.pid"
DEFAULT_ACTIONS = (ReportActionBinding, ReportActionInput, ReportActionStatus)


class DS4Controller(object):
    def __init__(self, index, options, dynamic=False):
        self.index = index
        self.dynamic = dynamic
        self.logger = Daemon.logger.new_module("controller {0}".format(index))

        self.actions = [cls(self) for cls in DEFAULT_ACTIONS]
        self.device = None
        self.default_profile = options
        self.inputs = {}
        self.profile_iterator = None
        self.joystick_layout = None

        if options.profiles and options.profile_toggle:
            self.profile_iterator = self.create_profile_iterator(options)
            self.actions[0].add_binding(options.profile_toggle,
                                        lambda: next(self.profile_iterator))

        if options.disconnect:
            self.actions[0].add_binding(options.disconnect,
                                        lambda: self.device.disconnect())

        self.load_options(options)

    def create_profile_iterator(self, options):
        profiles = dict(options.parent.profiles)
        profiles["default"] = options

        for next_profile in cycle(options.profiles + ["default"]):
            next_profile_options = profiles.get(next_profile)
            if next_profile_options:
                self.logger.info("Switching to profile: {0}", next_profile)
                self.load_options(next_profile_options)
            else:
                self.logger.warning("Ignoring invalid profile: {0}",
                                    next_profile)

            yield

    def setup_device(self, device, new_device=True):
        self.device = device
        self.device.set_led(*self.options.led)

        if new_device:
            # Reset the status of existing report actions
            for action in self.actions:
                action.reset()

    def load_options(self, options):
        self.options = options

        for action in self.actions:
            if type(action) not in DEFAULT_ACTIONS:
                self.actions.remove(action)

        if options.battery_flash:
            self.actions.append(ReportActionBattery(self))

        try:
            if self.options.mapping:
                joystick_layout = self.options.mapping
            elif self.options.emulate_xboxdrv:
                joystick_layout = "xboxdrv"
            elif self.options.emulate_xpad:
                joystick_layout = "xpad"
            elif self.options.emulate_xpad_wireless:
                joystick_layout = "xpad_wireless"
            else:
                joystick_layout = "ds4"

            if not self.inputs.get("mouse") and self.options.trackpad_mouse:
                self.inputs["mouse"] = create_uinput_device("mouse")
            elif self.inputs.get("mouse") and not self.options.trackpad_mouse:
                self.inputs["mouse"].device.close()
                self.inputs.pop("mouse", None)

            if "joystick" in self.inputs and self.joystick_layout != joystick_layout:
                self.inputs["joystick"].device.close()
                joystick = create_uinput_device(joystick_layout)
                self.inputs["joystick"] = joystick
            elif "joystick" not in self.inputs:
                joystick = create_uinput_device(joystick_layout)
                self.inputs["joystick"] = joystick
                if joystick.device.device:
                    self.logger.info("Created devices {0} (joystick) "
                                     "{1} (evdev) ", joystick.joystick_dev,
                                     joystick.device.device.fn)
            else:
                joystick = None

            if joystick:
                self.joystick_layout = joystick_layout

                # If the profile binding is a single button we don't want to
                # send it to the joystick at all
                if (self.profile_iterator and
                    len(self.default_profile.profile_toggle) == 1):
                    button = self.default_profile.profile_toggle[0]
                    self.inputs["joystick"].ignored_buttons.add(button)

        except DeviceError as err:
            Daemon.exit("Failed to create input device: {0}", err)

        if self.device:
            self.setup_device(self.device, new_device=False)

    def read_device(self, device):
        self.setup_device(device)

        for report in self.device.reports:
            for action in self.actions:
                action.handle_report(report)

        self.logger.info("Disconnected")
        self.device.close()


class ControllerAction(argparse.Action):
    __options__ = ["battery_flash", "emulate_xboxdrv", "emulate_xpad",
                   "emulate_xpad_wireless", "led", "mapping",
                   "profile_toggle", "profiles", "disconnect",
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
controllopt.add_argument("--led", metavar="color", default="0000ff",
                         type=hexcolor,
                         help="sets color of the LED. Uses hex color codes, "
                              "e.g. 'ff0000' is red. Default is '0000ff' (blue)")
controllopt.add_argument("--mapping", metavar="mapping",
                         help="use a custom button mapping specified in the "
                              "config file")
controllopt.add_argument("--profile-toggle", metavar="button(s)",
                         type=buttoncombo,
                         help="a button combo that will trigger profile "
                              "cycling, e.g. 'R1+L1+PS'")
controllopt.add_argument("--profiles", metavar="profiles",
                         type=stringlist,
                         help="profiles to cycle through using the button "
                              "specified by --profile-toggle, e.g. "
                              "'profile1,profile2'")
controllopt.add_argument("--disconnect", metavar="button(s)",
                         type=buttoncombo,
                         help="a button combo that will disconnect the device")
controllopt.add_argument("--trackpad-mouse", action="store_true",
                         help="makes the trackpad control the mouse")
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

    for name, section in config.sections("mapping"):
        mapping = config.section(section)
        parse_uinput_mapping(name, mapping)

    for controller in options.controllers:
        controller.parent = options

    return options


def main():
    options = load_options()

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
        controller = DS4Controller(index + 1, options)
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
            controller = DS4Controller(index, options, dynamic=True)
        else:
            controller = controllers.pop(0)

        controller.logger.info("Connected to {0}", device.name)

        thread = Thread(target=controller.read_device, args=(device,))
        thread.daemon = True
        thread.controller = controller
        thread.start()
        threads.append(thread)

if __name__ == "__main__":
    main()
