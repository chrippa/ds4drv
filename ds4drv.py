"""ds4drv - A DualShock 4 bluetooth driver for Linux."""

import argparse
import os
import subprocess
import socket
import sys

from collections import namedtuple
from time import time
from threading import Thread, Lock
from struct import Struct

from evdev import UInput, ecodes


CONTROLLER_LOG = "Controller {0}"
BLUETOOTH_LOG = "Bluetooth"

DAEMON_LOG_FILE = "~/.cache/ds4drv.log"

L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_GET_REPORT = 0x40
HIDP_TRANS_SET_REPORT = 0x50

HIDP_DATA_RTYPE_INPUT = 0x01
HIDP_DATA_RTYPE_OUTPUT = 0x02
HIDP_DATA_RTYPE_FEATURE = 0x03

S16LE = Struct("<h")

DS4Controller = namedtuple("DS4Controller", "id joypad options dynamic")

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
                        "charging"])


class Daemon(object):
    lock = Lock()
    output = sys.stdout

    @classmethod
    def fork(cls, logfile):
        cls.info("Forking into background, writing log to {0}", logfile)

        try:
            pid = os.fork()
        except OSError as err:
            cls.exit("Failed to fork: {0}", err)

        if pid == 0:
            os.setsid()

            try:
                pid = os.fork()
            except OSError as err:
                cls.exit("Failed to fork child process: {0}", err)

            if pid == 0:
                os.chdir("/")
                cls.open_log(logfile)
            else:
                sys.exit(0)
        else:
            sys.exit(0)

    @classmethod
    def open_log(cls, logfile):
        logfile = os.path.expanduser(logfile)
        dirname = os.path.dirname(logfile)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError as err:
                cls.exit("Failed to open log file: {0} ({1})", logfile, err)

        try:
            cls.output = open(logfile, "w")
        except OSError as err:
            cls.exit("Failed to open log file: {0} ({1})", logfile, err)

    @classmethod
    def msg(cls, prefix, fmt, *args, **kwargs):
        subprefix = kwargs.pop("subprefix", None)

        if subprefix:
            msg = "[{0}][{1}] ".format(prefix, subprefix)
        else:
            msg = "[{0}] ".format(prefix)

        msg += fmt.format(*args, **kwargs)

        with cls.lock:
            cls.output.write(msg + "\n")
            cls.output.flush()

    @classmethod
    def info(cls, *args, **kwargs):
        cls.msg("info", *args, **kwargs)

    @classmethod
    def warn(cls, *args, **kwargs):
        cls.msg("warning", *args, **kwargs)

    @classmethod
    def exit(cls, *args, **kwargs):
        cls.msg("error", *args, **kwargs)
        sys.exit(1)


class UInputDevice(object):
    def __init__(self, xpad=False, mouse=False):
        self.mouse = None

        if xpad:
            self.create_joypad_xpad()
        else:
            self.create_joypad_ds4()

        if mouse:
            self.create_mouse()

    def create_mouse(self):
        events = {
            ecodes.EV_REL: (ecodes.REL_X, ecodes.REL_Y),
            ecodes.EV_KEY: (ecodes.BTN_LEFT, ecodes.BTN_RIGHT)
        }
        self.mouse = UInput(events)
        self.mouse_pos = None

    def create_joypad(self, name, axes, buttons, hats, axes_options={}):
        events = {ecodes.EV_ABS: [], ecodes.EV_KEY: []}
        device_name = name

        for name in axes:
            key = getattr(ecodes, name)
            params = axes_options.get(name, (0, 255, 0, 0))
            events[ecodes.EV_ABS].append((key, params))

        for name in hats:
            key = getattr(ecodes, name)
            params = (-1, 1, 0, 0)
            events[ecodes.EV_ABS].append((key, params))

        for name in buttons:
            events[ecodes.EV_KEY].append(getattr(ecodes, name))

        self.joypad = UInput(name=device_name, events=events)
        self.axes = axes
        self.buttons = buttons
        self.hats = hats

    def create_joypad_ds4(self):
        axes_map = {
            "ABS_X":      "left_analog_x",
            "ABS_Y":      "left_analog_y",
            "ABS_Z":      "right_analog_x",
            "ABS_RZ":     "right_analog_y",
            "ABS_RX":     "l2_analog",
            "ABS_RY":     "r2_analog",
            "ABS_TILT_X": "motion_x",
            "ABS_TILT_Y": "motion_y",
            "ABS_WHEEL":  "motion_z"
        }
        axes_options = {
            "ABS_TILT_X": (-32767, 32767, 0, 0),
            "ABS_TILT_Y": (-32767, 32767, 0, 0),
            "ABS_WHEEL":  (-32767, 32767, 0, 0),
        }
        button_map = {
            "BTN_TR2":    "button_options",
            "BTN_MODE":   "button_ps",
            "BTN_TL2":    "button_share",
            "BTN_B":      "button_cross",
            "BTN_C":      "button_circle",
            "BTN_A":      "button_square",
            "BTN_X":      "button_triangle",
            "BTN_Y":      "button_l1",
            "BTN_Z":      "button_r1",
            "BTN_TL":     "button_l2",
            "BTN_TR":     "button_r2",
            "BTN_SELECT": "button_l3",
            "BTN_START":  "button_r3",
            "BTN_THUMBL": "button_trackpad"
        }
        hat_map = {
            "ABS_HAT0X": ("dpad_left", "dpad_right"),
            "ABS_HAT0Y": ("dpad_up", "dpad_down")
        }

        self.create_joypad(axes=axes_map, axes_options=axes_options,
                           buttons=button_map, hats=hat_map,
                           name="Sony Computer Entertainment Wireless Controller")

    def create_joypad_xpad(self):
        axes_map = {
            "ABS_X":  "left_analog_x",
            "ABS_Y":  "left_analog_y",
            "ABS_RX": "right_analog_x",
            "ABS_RY": "right_analog_y",
            "ABS_Z":  "l2_analog",
            "ABS_RZ": "r2_analog"
        }
        button_map = {
            "BTN_START":  "button_options",
            "BTN_MODE":   "button_ps",
            "BTN_SELECT": "button_share",
            "BTN_A":      "button_cross",
            "BTN_B":      "button_circle",
            "BTN_X":      "button_square",
            "BTN_Y":      "button_triangle",
            "BTN_TL":     "button_l1",
            "BTN_TR":     "button_r1",
            "BTN_THUMBL": "button_l3",
            "BTN_THUMBR": "button_r3"
        }
        hat_map = {
            "ABS_HAT0X": ("dpad_left", "dpad_right"),
            "ABS_HAT0Y": ("dpad_up", "dpad_down")
        }

        self.create_joypad(axes=axes_map, buttons=button_map, hats=hat_map,
                           name="Microsoft X-Box 360 pad")

    def emit(self, report):
        self.emit_joypad(report)

        if self.mouse:
            self.emit_mouse(report)

    def emit_joypad(self, report):
        for name, attr in self.axes.items():
            name = getattr(ecodes, name)
            value = getattr(report, attr)

            self.joypad.write(ecodes.EV_ABS, name, value)

        for name, attr in self.buttons.items():
            name = getattr(ecodes, name)
            value = getattr(report, attr)
            self.joypad.write(ecodes.EV_KEY, name, value)

        for name, attr in self.hats.items():
            name = getattr(ecodes, name)
            if getattr(report, attr[0]):
                value = -1
            elif getattr(report, attr[1]):
                value = 1
            else:
                value = 0

            self.joypad.write(ecodes.EV_ABS, name, value)

        self.joypad.syn()

    def emit_mouse(self, report):
        if report.trackpad_touch0_active:
            if not self.mouse_pos:
                self.mouse_pos = (report.trackpad_touch0_x,
                                  report.trackpad_touch0_y)

            sensitivity = 0.5
            rel_x = (report.trackpad_touch0_x - self.mouse_pos[0]) * sensitivity
            rel_y = (report.trackpad_touch0_y - self.mouse_pos[1]) * sensitivity

            self.mouse.write(ecodes.EV_REL, ecodes.REL_X, int(rel_x))
            self.mouse.write(ecodes.EV_REL, ecodes.REL_Y, int(rel_y))
            self.mouse_pos = (report.trackpad_touch0_x, report.trackpad_touch0_y)
        else:
            self.mouse_pos = None

        self.mouse.write(ecodes.EV_KEY, ecodes.BTN_LEFT,
                         int(report.button_trackpad))
        self.mouse.syn()


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

        self.control(led_red=255, led_green=255, led_blue=255)

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()

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

        buf = self.buf

        return DS4Report(
            # Left analog stick
            buf[4], buf[5],

            # Right analog stick
            buf[6], buf[7],

            # L2 and R2 analog
            buf[11], buf[12],

            # DPad up, down, left, right
            (buf[8] in (0, 1, 7)), (buf[8] in (3, 4, 5)),
            (buf[8] in (5, 6, 7)), (buf[8] in (1, 2, 3)),

            # Buttons ross, circle, square, triangle
            (buf[8] & 32) != 0, (buf[8] & 64) != 0,
            (buf[8] & 16) != 0, (buf[8] & 128) != 0,

            # L1, L2 and L3 buttons
            (buf[9] & 0x01) != 0, (buf[9] & 0x04) != 0, (buf[9] & 0x40) != 0,

            # R1, R2,and R3 buttons
            (buf[9] & 0x02) != 0, (buf[9] & 0x08) != 0, (buf[9] & 0x80) != 0,

            # Share and option buttons
            (buf[9] & 0x10) != 0, (buf[9] & 0x20) != 0,

            # Trackpad and PS buttons
            (buf[10] & 2) != 0, (buf[10] & 1) != 0,

            # Acceleration
            S16LE.unpack(buf[16:18])[0],
            S16LE.unpack(buf[18:20])[0],
            S16LE.unpack(buf[20:22])[0],

            # Orientation
            -(S16LE.unpack(buf[22:24])[0]),
            S16LE.unpack(buf[24:26])[0],
            S16LE.unpack(buf[26:28])[0],

            # Trackpad touch 1: id, active, x, y
            buf[38] & 0x7f, (buf[38] >> 7) == 0,
            ((buf[40] & 0x0f) << 8) | buf[39],
            buf[41] << 4 | ((buf[40] & 0xf0) >> 4),

            # Trackpad touch 2: id, active, x, y
            buf[42] & 0x7f, (buf[42] >> 7) == 0,
            ((buf[44] & 0x0f) << 8) | buf[43],
            buf[45] << 4 | ((buf[44] & 0xf0) >> 4),

            # Timestamp and battery
            buf[10] >> 2,
            buf[33] % 0x10,
            (buf[33] & 0x10) != 0
        )

    @property
    def reports(self):
        while True:
            report = self.read_report()

            if report is None:
                break

            if report:
                yield report
            else:
                Daemon.warn("Got simplified HID report, ignoring")


class ControllerAction(argparse.Action):
    __options__ = ["battery_flash", "emulate_xpad", "idle_timeout", "led",
                   "trackpad_mouse"]

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


def hexcolor(color):
    if len(color) != 6:
        raise ValueError

    values = (color[:2], color[2:4], color[4:6])
    values = map(lambda x: int(x, 16), values)

    return tuple(values)


parser = argparse.ArgumentParser(prog="ds4drv")
parser.add_argument("--daemon", action="store_true",
                    help="run in the background as a daemon")

controllopt = parser.add_argument_group("controller options")
controllopt.add_argument("--battery-flash", action="store_true",
                         help="flashes the LED once a minute if the "
                              "battery is low")
controllopt.add_argument("--emulate-xpad", action="store_true",
                         help="emulates the same joypad layout as a wired "
                              "Xbox 360 controller")
controllopt.add_argument("--idle-timeout", type=int, metavar="minutes",
                         default=15,
                         help="disconnects the controller if no button has "
                              "been pressed for <minutes>. 0 means no "
                              "idle timeout at all, default is 15 minutes")
controllopt.add_argument("--led", metavar="color", default="0000ff",
                         type=hexcolor,
                         help="sets color of the LED. Uses hex color codes, "
                              "e.g. 'ff0000' is red. Default is '0000ff' (blue)")
controllopt.add_argument("--trackpad-mouse", action="store_true",
                         help="makes the trackpad control the mouse")
controllopt.add_argument("--next-controller", nargs=0, action=ControllerAction,
                         help="creates another controller")


def bluetooth_check():
    try:
        subprocess.check_output(["hcitool", "clock"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        Daemon.exit("'hcitool clock' returned error. Make sure your "
                    "bluetooth device is on with 'hciconfig hciX up'.")
    except OSError:
        Daemon.exit("'hcitool' could not be found, make sure you have "
                    "bluez-utils installed.")


def bluetooth_scan():
    devices = []
    res = subprocess.check_output(["hcitool", "scan"], stderr=subprocess.STDOUT)
    res = res.splitlines()[1:]

    for _, bdaddr, name in map(lambda l: l.split(b"\t"), res):
        devices.append((bdaddr.decode("ascii"), name.decode("ascii")))

    return devices


def next_joypad_device():
    for i in range(100):
        dev = "/dev/input/js{0}".format(i)
        if not os.path.exists(dev):
            return dev


def create_controller(index, options, dynamic=False):
    js_device = next_joypad_device()
    joypad = UInputDevice(xpad=options.emulate_xpad,
                          mouse=options.trackpad_mouse)
    controller = DS4Controller(index, joypad, options, dynamic)

    Daemon.info("Created devices {0} (joypad) {1} (evdev)",
                js_device, joypad.joypad.device.fn,
                subprefix=CONTROLLER_LOG.format(controller.id))

    return controller


def find_device():
    devices = bluetooth_scan()
    for bdaddr, name in devices:
        if name == "Wireless Controller":
            Daemon.info("Found device {0}", bdaddr,
                        subprefix=BLUETOOTH_LOG)
            return DS4Device.connect(bdaddr)


def find_devices():
    log_msg = True
    while True:
        if log_msg:
            Daemon.info("Scanning for devices", subprefix=BLUETOOTH_LOG)

        try:
            device = find_device()
            if device:
                yield device
                log_msg = True
            else:
                log_msg = False
        except socket.error as err:
            Daemon.warn("Unable to connect to detected device: {0}", err,
                        subprefix=BLUETOOTH_LOG)
        except subprocess.CalledProcessError:
            Daemon.exit("'hcitool scan' returned error. Make sure your "
                        "bluetooth device is on with 'hciconfig hciX up'.")
        except OSError:
            Daemon.exit("'hcitool' could not be found, make sure you have "
                        "bluez-utils installed.")


def read_device(device, controller):
    options = controller.options
    device.control(led_red=options.led[0],
                   led_green=options.led[1],
                   led_blue=options.led[2])

    led_last_flash = time()
    led_flashing = True
    last_button_pressed = time()
    for report in device.reports:
        if options.battery_flash:
            if report.battery < 2 and not report.charging:
                if not led_flashing and (time() - led_last_flash) > 60:
                    device.control(led_red=options.led[0],
                                   led_green=options.led[1],
                                   led_blue=options.led[2],
                                   flash_led1=30, flash_led2=30)
                    led_flashing = True
                    led_last_flash = time()

            if led_flashing and (time() - led_last_flash) > 5:
                device.control(flash_led1=0, flash_led2=0)
                device.control(led_red=options.led[0],
                               led_green=options.led[1],
                               led_blue=options.led[2])
                led_flashing = False

        if options.idle_timeout:
            for field in report._fields:
                if field.startswith("button_") or field.startswith("dpad_"):
                    if getattr(report, field):
                        last_button_pressed = time()

            if ((time() - last_button_pressed) / 60) > options.idle_timeout:
                Daemon.info("Disconnecting due to idle timeout",
                            subprefix=CONTROLLER_LOG.format(controller.id))
                break

        controller.joypad.emit(report)

    Daemon.info("Disconnected",
                subprefix=CONTROLLER_LOG.format(controller.id))
    device.close()


def main():
    options = parser.parse_args(sys.argv[1:] + ["--next-controller"])

    bluetooth_check()

    if options.daemon:
        Daemon.fork(DAEMON_LOG_FILE)

    controllers = []
    threads = []

    for index, options in enumerate(options.controllers):
        controller = create_controller(index + 1, options)
        controllers.append(controller)

    for device in find_devices():
        for thread in threads:
            # Reclaim the joypad device if the controller is gone
            if not thread.is_alive():
                if not thread.controller.dynamic:
                    controllers.insert(0, thread.controller)
                threads.remove(thread)

        # No pre-configured controller available,
        # create one with default settings
        if not controllers:
            index = len(threads) + 1
            options = ControllerAction.default_controller()
            controller = create_controller(index, options, dynamic=True)
        else:
            controller = controllers.pop(0)

        Daemon.info("Connected to {0}", device.bdaddr,
                    subprefix=CONTROLLER_LOG.format(controller.id))

        thread = Thread(target=read_device, args=(device, controller))
        thread.daemon = True
        thread.controller = controller
        thread.start()
        threads.append(thread)
