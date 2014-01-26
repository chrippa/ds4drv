import socket
import sys

from collections import namedtuple
from struct import Struct

from .daemon import Daemon


L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_GET_REPORT = 0x40
HIDP_TRANS_SET_REPORT = 0x50

HIDP_DATA_RTYPE_INPUT   = 0x01
HIDP_DATA_RTYPE_OUTPUT  = 0x02
HIDP_DATA_RTYPE_FEATURE = 0x03

S16LE = Struct("<h")

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
    @classmethod
    def connect(cls, addr):
        ctl_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        ctl_socket.connect((addr, L2CAP_PSM_HIDP_CTRL))

        int_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        int_socket.connect((addr, L2CAP_PSM_HIDP_INTR))

        return cls(addr, ctl_socket, int_socket)

    def __init__(self, bdaddr, ctl_sock, int_sock):
        self.bdaddr = bdaddr
        self.buf = bytearray(79)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock

        self._led = (0, 0, 0)
        self._led_flash = (0, 0)
        self._led_flashing = False

        self.set_led(255, 255, 255)

    def _control(self, **kwargs):
        self.control(led_red=self._led[0], led_green=self._led[1],
                     led_blue=self._led[2], flash_led1=self._led_flash[0],
                     flash_led2=self._led_flash[1], **kwargs)

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()

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
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT,))
        pkt = bytearray(78)
        pkt[0] = 0x11
        pkt[1] = 128
        pkt[3] = 255

        # Rumble
        pkt[6] = big_rumble
        pkt[7] = small_rumble

        # LED (red, green, blue)
        pkt[8] = led_red
        pkt[9] = led_green
        pkt[10] = led_blue

        # Time to flash bright (255 = 2.5 seconds)
        pkt[11] = flash_led1

        # Time to flash dark (255 = 2.5 seconds)
        pkt[12] = flash_led2

        self.ctl_sock.sendall(bytes(hid + pkt))

    def read_report(self):
        ret = self.int_sock.recv_into(self.buf)

        # Disconnection
        if ret == 0:
            return

        # Invalid report size, just ignore it
        if ret < 79:
            return False

        # No need for a extra copy on Python 3.3+
        if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
            buf = memoryview(self.buf)
        else:
            buf = self.buf

        # Cut off bluetooth data
        buf = buf[3:]

        return self.parse_report(buf)

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
            else:
                Daemon.warn("Got simplified HID report, ignoring")
