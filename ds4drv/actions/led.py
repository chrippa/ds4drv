from ..action import ReportAction
from ..config import hexcolor

BATTERY_MAX          = 9
BATTERY_MAX_CHARGING = 11
DEFAULT_COLORS       = [(255,0,0),(255,255,0),(0,255,0),(0,255,255),(0,0,255)]

ReportAction.add_option("--led", metavar="color", nargs="*", type=hexcolor,
                  help="Sets color of the LED using hex color codes, "
                       "e.g. 'ff0000' or 'f00' is red. With multiple "
                       "colors, fades by increasing battery level; "
                       "with none, uses a default fade palette")


class ReportActionLED(ReportAction):
    """Sets the LED color on the device."""

    def __init__(self, *args, **kwargs):
        super(ReportActionLED, self).__init__(*args, **kwargs)

        self.colors = None
        self.handle_next = False
        self.timer = self.create_timer(15, self.check_battery)

    def setup(self, device):
        self.update()

    def load_options(self, options):
        if options.led is None:
            self.colors = None
        else:
            self.colors = DEFAULT_COLORS if len(options.led) < 1 else list(options.led)
            if len(self.colors) == 1:
                self.colors.append(self.colors[0])
        self.update()

    def update(self):
        if self._last_report:
            self.check_battery(self._last_report)

        if self.controller.device and self.colors and len(self.colors) > 1:
            self.enable()
        else:
            self.disable()

    def enable(self):
        self.handle_next = True
        self.timer.start()

    def disable(self):
        self.handle_next = False
        self.timer.stop()

    def handle_report(self, report):
        if self.handle_next:
            self.handle_next = False
            self.check_battery(report)

    def check_battery(self, report):
        if self.colors and self.controller.device:
            battery = max(0, report.battery)
            battery_max = max(battery, BATTERY_MAX_CHARGING if report.plug_usb else BATTERY_MAX)
            battery_lvl = float(battery) / battery_max
            index_max = len(self.colors) - 1
            index = min(int(battery_lvl * index_max), index_max - 1)
            color0 = self.colors[index]
            color1 = self.colors[index + 1]
            weight1 = min(max(battery_lvl * index_max - index, 0.0), 1.0)
            weight0 = 1.0 - weight1
            color_r = int(weight0 * color0[0] + weight1 * color1[0] + 0.5)
            color_g = int(weight0 * color0[1] + weight1 * color1[1] + 0.5)
            color_b = int(weight0 * color0[2] + weight1 * color1[2] + 0.5)
            self.controller.device.set_led(color_r, color_g, color_b)

        return True
