import argparse
import os
import re
import sys

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from functools import partial
from operator import attrgetter

from . import __version__
from .uinput import parse_uinput_mapping
from .utils import parse_button_combo


CONFIG_FILES = ("~/.config/ds4drv.conf", "/etc/ds4drv.conf")
DAEMON_LOG_FILE = "~/.cache/ds4drv.log"
DAEMON_PID_FILE = "/tmp/ds4drv.pid"


class SortingHelpFormatter(argparse.HelpFormatter):
    def add_argument(self, action):
        # Force the built in options to be capitalized
        if action.option_strings[-1] in ("--version", "--help"):
            action.help = action.help.capitalize()

        super(SortingHelpFormatter, self).add_argument(action)
        self.add_text("")

    def start_section(self, heading):
        heading = heading.capitalize()
        return super(SortingHelpFormatter, self).start_section(heading)

    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter("option_strings"))
        super(SortingHelpFormatter, self).add_arguments(actions)


parser = argparse.ArgumentParser(prog="ds4drv",
                                 formatter_class=SortingHelpFormatter)
parser.add_argument("--version", action="version",
                    version="%(prog)s {0}".format(__version__))

configopt = parser.add_argument_group("configuration options")
configopt.add_argument("--config", metavar="filename",
                       type=os.path.expanduser,
                       help="Configuration file to read settings from. "
                            "Default is ~/.config/ds4drv.conf or "
                            "/etc/ds4drv.conf, whichever is found first")

backendopt = parser.add_argument_group("backend options")
backendopt.add_argument("--hidraw", action="store_true",
                        help="Use hidraw devices. This can be used to access "
                             "USB and paired bluetooth devices. Note: "
                             "Bluetooth devices does currently not support "
                             "any LED functionality")

daemonopt = parser.add_argument_group("daemon options")
daemonopt.add_argument("--daemon", action="store_true",
                       help="Run in the background as a daemon")
daemonopt.add_argument("--daemon-log", default=DAEMON_LOG_FILE, metavar="file",
                       help="Log file to create in daemon mode")
daemonopt.add_argument("--daemon-pid", default=DAEMON_PID_FILE, metavar="file",
                       help="PID file to create in daemon mode")

controllopt = parser.add_argument_group("controller options")


class Config(configparser.SafeConfigParser):
    def load(self, filename):
        self.read([filename])

    def section_to_args(self, section):
        args = []

        for key, value in self.section(section).items():
            if value.lower() == "true":
                args.append("--{0}".format(key))
            elif value.lower() == "false":
                pass
            else:
                args.append("--{0}={1}".format(key, value))

        return args

    def section(self, section, key_type=str, value_type=str):
        try:
            # Removes empty values and applies types
            return dict(map(lambda kv: (key_type(kv[0]), value_type(kv[1])),
                            filter(lambda i: bool(i[1]),
                                   self.items(section))))
        except configparser.NoSectionError:
            return {}

    def sections(self, prefix=None):
        for section in configparser.SafeConfigParser.sections(self):
            match = re.match(r"{0}:(.+)".format(prefix), section)
            if match:
                yield match.group(1), section

    def controllers(self):
        controller_sections = dict(self.sections("controller"))
        if not controller_sections:
            return ["--next-controller"]

        last_controller = max(map(lambda c: int(c[0]), controller_sections))
        args = []
        for i in range(1, last_controller + 1):
            section = controller_sections.get(str(i))
            if section:
                for arg in self.section_to_args(section):
                    args.append(arg)

            args.append("--next-controller")

        return args


class ControllerAction(argparse.Action):
    # These options are moved from the normal options namespace to
    # a controller specific namespace on --next-controller.
    __options__ = []

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

controllopt.add_argument("--next-controller", nargs=0, action=ControllerAction,
                         help="Creates another controller")

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
        for key, attr in mapping.items():
            if '#' in attr: # Remove tailing comments on the line
                attr = attr.split('#', 1)[0].rstrip()
                mapping[key] = attr
        parse_uinput_mapping(name, mapping)

    for controller in options.controllers:
        controller.parent = options

    options.default_controller = ControllerAction.default_controller()
    options.default_controller.parent = options

    return options


def add_controller_option(name, **options):
    option_name = name[2:].replace("-", "_")
    controllopt.add_argument(name, **options)
    ControllerAction.__options__.append(option_name)


add_controller_option("--profiles", metavar="profiles",
                      type=stringlist,
                      help="Profiles to cycle through using the button "
                           "specified by --profile-toggle, e.g. "
                           "'profile1,profile2'")

