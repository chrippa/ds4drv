from ..action import ReportAction

BATTERY_MAX          = 8
BATTERY_MAX_CHARGING = 11


class ReportActionStatus(ReportAction):
    """Reports device statuses such as battery percentage to the log."""

    def __init__(self, *args, **kwargs):
        super(ReportActionStatus, self).__init__(*args, **kwargs)
        self.timer = self.create_timer(1, self.check_status)

    def setup(self, device):
        self.report = None
        self.timer.start()

    def disable(self):
        self.timer.stop()

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
