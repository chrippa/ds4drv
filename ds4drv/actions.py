import os
import subprocess

from collections import namedtuple
from time import time


BATTERY_MAX          = 8
BATTERY_MAX_CHARGING = 11
BATTERY_WARNING      = 2

BINDING_ACTIONS = {}


class ReportTimer(object):
    def __init__(self, interval):
        self.interval = interval
        self.time = time()

    def passed(self):
        now = time()
        if (now - self.time) > self.interval:
            self.time = now
            return True

        return False


class ReportAction(object):
    def __init__(self, controller):
        self.controller = controller
        self.timers = {}

    def add_timer(self, interval, func):
        self.timers[func] = ReportTimer(interval)

    def handle_report(self, report):
        for func, timer in self.timers.items():
            if timer.passed():
                repeat = func(report)
                if not repeat:
                    self.timers.pop(func, None)

    def reset(self):
        pass


class ReportActionBattery(ReportAction):
    def __init__(self, controller):
        super(ReportActionBattery, self).__init__(controller)

        self.add_timer(60, self.check_battery)

    def check_battery(self, report):
        if report.battery < BATTERY_WARNING and not report.plug_usb:
            self.controller.device.start_led_flash(30, 30)
            self.add_timer(5, lambda r: self.controller.device.stop_led_flash())

        return True


ActionBinding = namedtuple("ActionBinding", "callback args sticky")

class ReportActionBinding(ReportAction):
    def __init__(self, controller):
        super(ReportActionBinding, self).__init__(controller)

        self.bindings = {}
        self.active = set()

    def add_binding(self, combo, callback, args=(), sticky=False):
        self.bindings[combo] = ActionBinding(callback, args, sticky)

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

    def reset(self):
        self.active = set()
        self.bindings = dict(filter(lambda kv: kv[1].sticky,
                                    self.bindings.items()))

class ReportActionInput(ReportAction):
    def handle_report(self, report):
        for name, input in self.controller.inputs.items():
            input.emit(report)


class ReportActionStatus(ReportAction):
    def __init__(self, controller):
        super(ReportActionStatus, self).__init__(controller)

        self.report = None
        self.add_timer(1, self.check_status)

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

            self.controller.logger.info("USB: {0}", plug_usb)

        # Battery level
        if self.report.battery != report.battery or show_battery:
            max_value = report.plug_usb and BATTERY_MAX_CHARGING or BATTERY_MAX
            battery = 100 * report.battery // max_value

            if battery < 100:
                self.controller.logger.info("Battery: {0}%", battery)
            else:
                self.controller.logger.info("Battery: Fully charged")

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

            self.controller.logger.info("Audio: {0}", plug_audio)

        self.report = report

        return True

    def reset(self):
        self.report = None


class ReportActionDump(ReportAction):
    def __init__(self, controller):
        super(ReportActionDump, self).__init__(controller)

        dump_interval = 0.02
        self.add_timer(dump_interval, self.dump)

    def dump(self, report):
        dump = "Report dump\n"
        for key, value in report._asdict().items():
            dump += "    {0}: {1}\n".format(key, value)

        self.controller.logger.info(dump)

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
    controller.next_profile()


@bindingaction("load-profile")
def _load_profile(controller, profile):
    controller.load_profile(profile)

