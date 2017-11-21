from ..action import ReportAction

BATTERY_WARNING = 2

ReportAction.add_option("--battery-flash", action="store_true",
                        help="Flashes the LED once a minute if the "
                             "battery is low")


class ReportActionBattery(ReportAction):
    """Flashes the LED when battery is low."""

    def __init__(self, *args, **kwargs):
        super(ReportActionBattery, self).__init__(*args, **kwargs)

        self.timer_check = self.create_timer(60, self.check_battery)
        self.timer_flash = self.create_timer(5, self.stop_flash)

    def enable(self):
        self.timer_check.start()

    def disable(self):
        self.timer_check.stop()
        self.timer_flash.stop()

    def load_options(self, options):
        if options.battery_flash:
            self.enable()
        else:
            self.disable()

    def stop_flash(self, report):
        self.controller.device.stop_led_flash()

    def check_battery(self, report):
        if report.battery < BATTERY_WARNING and not report.plug_usb:
            self.controller.device.start_led_flash(30, 30)
            self.timer_flash.start()

        return True
