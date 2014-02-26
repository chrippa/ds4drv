import os
import re
import shlex
import subprocess

from collections import namedtuple
from functools import wraps
from itertools import chain

from .exceptions import DeviceError
from .uinput import create_uinput_device


BATTERY_MAX          = 8
BATTERY_MAX_CHARGING = 11
BATTERY_WARNING      = 2

BINDING_ACTIONS = {}


class ReportAction(object):
    def __init__(self, controller):
        self.controller = controller
        self.logger = controller.logger
        self._last_report = None

        self.register_event("device-setup", self.setup)
        self.register_event("device-cleanup", self.disable)
        self.register_event("load-options", self.load_options)

    def add_timer(self, interval, func):
        @wraps(func)
        def wrapper():
            if self._last_report:
                return func(self._last_report)
            return True

        self.controller.loop.add_timer(interval, wrapper)

    def remove_timer(self, func):
        self.controller.loop.remove_timer(func)

    def register_event(self, event, func):
        self.controller.loop.register_event(event, func)

    def unregister_event(self, event, func):
        self.controller.loop.unregister_event(event, func)

    def handle_report(self, report):
        self._last_report = report

    def setup(self, device):
        pass

    def enable(self):
        pass

    def disable(self):
        pass

    def load_options(self, options):
        pass


class ReportActionBattery(ReportAction):
    def enable(self):
        self.add_timer(60, self.check_battery)

    def disable(self):
        self.remove_timer(self.check_battery)
        self.remove_timer(self.stop_flash)

    def load_options(self, options):
        self.disable()

        if options.battery_flash:
            self.enable()

    def stop_flash(self, report):
        self.controller.device.stop_led_flash()

    def check_battery(self, report):
        if report.battery < BATTERY_WARNING and not report.plug_usb:
            self.controller.device.start_led_flash(30, 30)
            self.add_timer(5, self.stop_flash)

        return True


ActionBinding = namedtuple("ActionBinding", "callback args")

class ReportActionBinding(ReportAction):
    def __init__(self, controller):
        super(ReportActionBinding, self).__init__(controller)

        self.bindings = {}
        self.active = set()

    def add_binding(self, combo, callback, *args):
        self.bindings[combo] = ActionBinding(callback, args)

    def load_options(self, options):
        self.active = set()
        self.bindings = {}

        bindings = (self.controller.bindings["global"].items(),
                    self.controller.bindings.get(options.bindings, {}).items())

        for binding, action in chain(*bindings):
            self.add_binding(binding, self.handle_binding_action, action)

        have_profiles = (self.controller.profiles and
                         len(self.controller.profiles) > 1)
        if have_profiles and self.controller.default_profile.profile_toggle:
            self.add_binding(self.controller.default_profile.profile_toggle,
                             lambda r: self.controller.next_profile())

    def handle_binding_action(self, report, action):
        info = dict(name=self.controller.device.name,
                    profile=self.controller.current_profile,
                    device_addr=self.controller.device.device_addr,
                    report=report)

        def replace_var(match):
            var, attr = match.group("var", "attr")
            var = info.get(var)
            if attr:
                var = getattr(var, attr, None)
            return str(var)

        action = re.sub(r"\$(?P<var>\w+)(\.(?P<attr>\w+))?",
                        replace_var, action)
        action_split = shlex.split(action)
        action_type = action_split[0]
        action_args = action_split[1:]

        func = BINDING_ACTIONS.get(action_type)
        if func:
            try:
                func(self.controller, *action_args)
            except Exception as err:
                self.logger.error("Failed to execute action: {0}", err)
        else:
            self.logger.error("Invalid action type: {0}", action_type)

    def handle_report(self, report):
        for combo, action in self.bindings.items():
            modifiers = all(getattr(report, button) for button in combo[:-1])
            active = getattr(report, combo[-1])
            released = not active

            if modifiers and active and combo not in self.active:
                self.active.add(combo)
            elif released and combo in self.active:
                self.active.remove(combo)
                action.callback(report, *action.args)


class ReportActionInput(ReportAction):
    def __init__(self, controller):
        super(ReportActionInput, self).__init__(controller)

        self.joystick = None
        self.joystick_layout = None
        self.mouse = None

    def setup(self, device):
        # USB has a report frequency of 4 ms while BT is 2 ms, so we
        # use 5 ms between each mouse emit to keep it consistent and to
        # allow for at least one fresh report to be received inbetween
        self.add_timer(0.005, self.emit_mouse)

    def disable(self):
        self.remove_timer(self.emit_mouse)

    def load_options(self, options):
        try:
            if options.mapping:
                joystick_layout = options.mapping
            elif options.emulate_xboxdrv:
                joystick_layout = "xboxdrv"
            elif options.emulate_xpad:
                joystick_layout = "xpad"
            elif options.emulate_xpad_wireless:
                joystick_layout = "xpad_wireless"
            else:
                joystick_layout = "ds4"

            if not self.mouse and options.trackpad_mouse:
                self.mouse = create_uinput_device("mouse")
            elif self.mouse and not options.trackpad_mouse:
                self.mouse.device.close()
                self.mouse = None

            if self.joystick and self.joystick_layout != joystick_layout:
                self.joystick.device.close()
                joystick = create_uinput_device(joystick_layout)
                self.joystick = joystick
            elif not self.joystick:
                joystick = create_uinput_device(joystick_layout)
                self.joystick = joystick
                if joystick.device.device:
                    self.logger.info("Created devices {0} (joystick) "
                                     "{1} (evdev) ", joystick.joystick_dev,
                                     joystick.device.device.fn)
            else:
                joystick = None

            self.joystick.ignored_buttons = set()
            for button in options.ignored_buttons:
                self.joystick.ignored_buttons.add(button)

            if joystick:
                self.joystick_layout = joystick_layout

                # If the profile binding is a single button we don't want to
                # send it to the joystick at all
                if (self.controller.profiles and
                    self.controller.default_profile.profile_toggle and
                    len(self.controller.default_profile.profile_toggle) == 1):

                    button = self.controller.default_profile.profile_toggle[0]
                    self.joystick.ignored_buttons.add(button)
        except DeviceError as err:
            self.controller.exit("Failed to create input device: {0}", err)

    def emit_mouse(self, report):
        if self.joystick:
            self.joystick.emit_mouse(report)

        if self.mouse:
            self.mouse.emit_mouse(report)

        return True

    def handle_report(self, report):
        if self.joystick:
            self.joystick.emit(report)

        if self.mouse:
            self.mouse.emit(report)

        super(ReportActionInput, self).handle_report(report)


class ReportActionLED(ReportAction):
    def setup(self, device):
        device.set_led(*self.controller.options.led)

    def load_options(self, options):
        if self.controller.device:
            self.controller.device.set_led(*options.led)


class ReportActionStatus(ReportAction):
    def setup(self, device):
        self.report = None
        self.add_timer(1, self.check_status)

    def disable(self):
        self.remove_timer(self.check_status)

    def check_status(self, report):
        if not self.report:
            self.report = report
            show_battery = True
        else:
            show_battery = False

        # USB cable
        if self.report.plug_usb != report.plug_usb:
            plug_usb = report.plug_usb and "Connected" or "Disconnected"
            show_battery = True

            self.logger.info("USB: {0}", plug_usb)

        # Battery level
        if self.report.battery != report.battery or show_battery:
            max_value = report.plug_usb and BATTERY_MAX_CHARGING or BATTERY_MAX
            battery = 100 * report.battery // max_value

            if battery < 100:
                self.logger.info("Battery: {0}%", battery)
            else:
                self.logger.info("Battery: Fully charged")

        # Audio cable
        if (self.report.plug_audio != report.plug_audio or
            self.report.plug_mic != report.plug_mic):

            if report.plug_audio and report.plug_mic:
                plug_audio = "Headset"
            elif report.plug_audio:
                plug_audio = "Headphones"
            elif report.plug_mic:
                plug_audio = "Mic"
            else:
                plug_audio = "Speaker"

            self.logger.info("Audio: {0}", plug_audio)

        self.report = report

        return True


class ReportActionDump(ReportAction):
    def enable(self):
        self.add_timer(0.02, self.dump)

    def disable(self):
        self.remove_timer(self.dump)

    def load_options(self, options):
        self.disable()

        if options.dump_reports:
            self.enable()

    def dump(self, report):
        dump = "Report dump\n"
        for key in report.__slots__:
            value = getattr(report, key)
            dump += "    {0}: {1}\n".format(key, value)

        self.logger.info(dump)

        return True


def bindingaction(name):
    def decorator(func):
        BINDING_ACTIONS[name] = func
        return func
    return decorator


@bindingaction("exec")
def _exec(controller, cmd, *args):
    controller.logger.info("Executing: {0} {1}", cmd, " ".join(args))

    try:
        subprocess.check_call([cmd] + list(args))
    except (OSError, subprocess.CalledProcessError) as err:
        controller.logger.error("Failed to execute process: {0}", err)


@bindingaction("exec-background")
def _exec_background(controller, cmd, *args):
    controller.logger.info("Executing in the background: {0} {1}",
                           cmd, " ".join(args))

    try:
        subprocess.Popen([cmd] + list(args),
                         stdout=open(os.devnull, "wb"),
                         stderr=open(os.devnull, "wb"))
    except OSError as err:
        controller.logger.error("Failed to execute process: {0}", err)


@bindingaction("next-profile")
def _next_profile(controller):
    controller.next_profile()


@bindingaction("prev-profile")
def _prev_profile(controller):
    controller.prev_profile()


@bindingaction("load-profile")
def _load_profile(controller, profile):
    controller.load_profile(profile)

