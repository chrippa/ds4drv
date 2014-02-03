from time import time

BATTERY_MAX          = 8
BATTERY_MAX_CHARGING = 11
BATTERY_WARNING      = 2


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
    def __init__(self, device, controller):
        self.device = device
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


class ReportActionBattery(ReportAction):
    def __init__(self, device, controller):
        super(ReportActionBattery, self).__init__(device, controller)

        self.add_timer(60, self.check_battery)

    def check_battery(self, report):
        if report.battery < BATTERY_WARNING and not report.plug_usb:
            self.device.start_led_flash(30, 30)
            self.add_timer(5, lambda r: self.device.stop_led_flash())

        return True


class ReportActionInput(ReportAction):
    def handle_report(self, report):
        for input in self.controller.inputs:
            input.emit(report)


class ReportActionStatus(ReportAction):
    def __init__(self, device, controller):
        super(ReportActionStatus, self).__init__(device, controller)

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
