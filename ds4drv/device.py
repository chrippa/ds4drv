from collections import namedtuple
from struct import Struct


class StructHack(Struct):
    """Python <2.7.4 doesn't support struct unpack from bytearray"""
    def unpack(self, buf):
        if isinstance(buf, bytearray):
            buf = bytes(buf)

        return Struct.unpack(self, buf)

S16LE = StructHack("<h")

DS4Report = namedtuple("DS4Report",
                       ["left_analog_x",
                        "left_analog_y",
                        "right_analog_x",
                        "right_analog_y",
                        "l2_analog",
                        "r2_analog",
                        "dpad_up",
                        "dpad_down",
                        "dpad_left",
                        "dpad_right",
                        "button_cross",
                        "button_circle",
                        "button_square",
                        "button_triangle",
                        "button_l1",
                        "button_l2",
                        "button_l3",
                        "button_r1",
                        "button_r2",
                        "button_r3",
                        "button_share",
                        "button_options",
                        "button_trackpad",
                        "button_ps",
                        "motion_y",
                        "motion_x",
                        "motion_z",
                        "orientation_roll",
                        "orientation_yaw",
                        "orientation_pitch",
                        "trackpad_touch0_id",
                        "trackpad_touch0_active",
                        "trackpad_touch0_x",
                        "trackpad_touch0_y",
                        "trackpad_touch1_id",
                        "trackpad_touch1_active",
                        "trackpad_touch1_x",
                        "trackpad_touch1_y",
                        "timestamp",
                        "battery",
                        "plug_usb",
                        "plug_audio",
                        "plug_mic"])


class DS4Device(object):
    def __init__(self, device_name, device_addr, type):
        self.device_name = device_name
        self.device_addr = device_addr
        self.type = type

        self._led = (0, 0, 0)
        self._led_flash = (0, 0)
        self._led_flashing = False

        self.set_operational()

    def _control(self, **kwargs):
        self.control(led_red=self._led[0], led_green=self._led[1],
                     led_blue=self._led[2], flash_led1=self._led_flash[0],
                     flash_led2=self._led_flash[1], **kwargs)

    def rumble(self, small=0, big=0):
        self._control(small_rumble=small, big_rumble=big)

    def set_led(self, red=0, green=0, blue=0):
        self._led = (red, green, blue)
        self._control()

    def start_led_flash(self, on, off):
        if not self._led_flashing:
            self._led_flash = (on, off)
            self._led_flashing = True
            self._control()

    def stop_led_flash(self):
        if self._led_flashing:
            self._led_flash = (0, 0)
            self._led_flashing = False
            # Call twice, once to stop flashing...
            self._control()
            # ...and once more to make sure LED is set.
            self._control()

    def control(self, big_rumble=0, small_rumble=0,
                led_red=0, led_green=0, led_blue=0,
                flash_led1=0, flash_led2=0):
        if self.type == "bluetooth":
            pkt = bytearray(77)
            pkt[0] = 128
            pkt[2] = 255
            offset = 2
            report_id = 0x11

        elif self.type == "usb":
            pkt = bytearray(31)
            pkt[0] = 255
            offset = 0
            report_id = 0x05

        # Rumble
        pkt[offset+3] = big_rumble
        pkt[offset+4] = small_rumble

        # LED (red, green, blue)
        pkt[offset+5] = led_red
        pkt[offset+6] = led_green
        pkt[offset+7] = led_blue

        # Time to flash bright (255 = 2.5 seconds)
        pkt[offset+8] = flash_led1

        # Time to flash dark (255 = 2.5 seconds)
        pkt[offset+9] = flash_led2

        self.write_report(report_id, pkt)

    def parse_report(self, buf):
        dpad = buf[5] % 16

        return DS4Report(
            # Left analog stick
            buf[1], buf[2],

            # Right analog stick
            buf[3], buf[4],

            # L2 and R2 analog
            buf[8], buf[9],

            # DPad up, down, left, right
            (dpad in (0, 1, 7)), (dpad in (3, 4, 5)),
            (dpad in (5, 6, 7)), (dpad in (1, 2, 3)),

            # Buttons cross, circle, square, triangle
            (buf[5] & 32) != 0, (buf[5] & 64) != 0,
            (buf[5] & 16) != 0, (buf[5] & 128) != 0,

            # L1, L2 and L3 buttons
            (buf[6] & 1) != 0, (buf[6] & 4) != 0, (buf[6] & 64) != 0,

            # R1, R2,and R3 buttons
            (buf[6] & 2) != 0, (buf[6] & 8) != 0, (buf[6] & 128) != 0,

            # Share and option buttons
            (buf[6] & 16) != 0, (buf[6] & 32) != 0,

            # Trackpad and PS buttons
            (buf[7] & 2) != 0, (buf[7] & 1) != 0,

            # Acceleration
            S16LE.unpack(buf[13:15])[0],
            S16LE.unpack(buf[15:17])[0],
            S16LE.unpack(buf[17:19])[0],

            # Orientation
            -(S16LE.unpack(buf[19:21])[0]),
            S16LE.unpack(buf[21:23])[0],
            S16LE.unpack(buf[23:25])[0],

            # Trackpad touch 1: id, active, x, y
            buf[35] & 0x7f, (buf[35] >> 7) == 0,
            ((buf[37] & 0x0f) << 8) | buf[36],
            buf[38] << 4 | ((buf[37] & 0xf0) >> 4),

            # Trackpad touch 2: id, active, x, y
            buf[39] & 0x7f, (buf[39] >> 7) == 0,
            ((buf[41] & 0x0f) << 8) | buf[40],
            buf[42] << 4 | ((buf[41] & 0xf0) >> 4),

            # Timestamp and battery
            buf[7] >> 2,
            buf[30] % 16,

            # External inputs (usb, audio, mic)
            (buf[30] & 16) != 0, (buf[30] & 32) != 0,
            (buf[30] & 64) != 0
        )

    def read_report(self):
        pass

    def write_report(self, report_id, data):
        pass

    def set_operational(self):
        pass

    def close(self):
        pass

    @property
    def name(self):
        if self.type == "bluetooth":
            type_name = "Bluetooth"
        elif self.type == "usb":
            type_name = "USB"

        return "{0} Controller ({1})".format(type_name, self.device_name)

    @property
    def reports(self):
        while True:
            try:
                report = self.read_report()
            except (OSError, IOError):
                break

            if report is None:
                break

            if report:
                yield report
