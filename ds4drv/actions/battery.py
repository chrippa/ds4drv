import socket
from ..action import ReportAction

# Transmitter settings
UDP_IP = "127.0.0.1"
UDP_PORT = 54321

BATTERY_WARNING = 2

ReportAction.add_option("--battery-flash", action="store_true",
                        help="Flashes the LED once a minute if the "
                             "battery is low")


class ReportActionBattery(ReportAction):
    """Flashes the LED when battery is low and reports via UDP."""

    def __init__(self, *args, **kwargs):
        super(ReportActionBattery, self).__init__(*args, **kwargs)

        self.timer_check = self.create_timer(5, self.check_battery)
        self.timer_flash = self.create_timer(5, self.stop_flash)

    def enable(self):
        self.timer_check.start()

    def disable(self):
        self.timer_check.stop()
        self.timer_flash.stop()

    def load_options(self, options):
        self.battery_flash = options.battery_flash
        self.enable()  # Forces timer_check.start() regardless of the flag.

    def stop_flash(self, report):
        self.controller.device.stop_led_flash()

    def check_battery(self, report):
        if report.battery is not None:
            try:
                # ds4drv can return an object or a raw number (0-11)
                val = report.battery
                raw_str = str(val).lower()

                if any(x in raw_str for x in ["full", "max", "charged"]):
                    percentage = 100
                else:
                    # Extrai apenas os números
                    digits = "".join(filter(str.isdigit, raw_str))
                    num = int(digits) if digits else 0

                    # If the number is <= 11, it is the raw DS4 level (0-8 normal, 9-11 charging).
                    # Converts to 0-100 scale
                    if num <= 11:
                        # 8 is the maximum standard DS4 level when not connected via cable.
                        percentage = min(100, int((num / 8) * 100))
                    else:
                        percentage = num

                msg = f"{self.controller.index}:{percentage}"
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(msg.encode(), (UDP_IP, UDP_PORT))
                sock.close()
            except Exception:
                pass

        return True
