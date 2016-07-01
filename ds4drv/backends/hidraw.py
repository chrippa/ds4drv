import fcntl
import itertools
import os
import struct
import signal

import signal
from multiprocessing import Pool

from io import FileIO
from time import sleep

from evdev import InputDevice
from pyudev import Context, Monitor

from ..backend import Backend
from ..exceptions import DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice


IOC_RW = 3221243904
HIDIOCSFEATURE = lambda size: IOC_RW | (0x06 << 0) | (size << 16)
HIDIOCGFEATURE = lambda size: IOC_RW | (0x07 << 0) | (size << 16)


class HidrawWriter:
    def __init__(self, hidraw_device, *args, **kwargs):
        super(HidrawWriter, self).__init__(*args, **kwargs)

        self.hidraw_device = hidraw_device

        self.write_pool = Pool(
            processes = 1,
            initializer = HidrawWriter.pool_init, initargs = (hidraw_device,)
        )

    @staticmethod
    def pool_init(hidraw_device):
        # Signals have been inherited from the parent. In particular,
        # the cleanup signals from __main__. Signals are completely ignored
        # here since Pool hangs otherwise.
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        HidrawWriter.report_fd = os.open(hidraw_device, os.O_RDWR | os.O_NONBLOCK)
        HidrawWriter.fd = FileIO(HidrawWriter.report_fd, "rb+", closefd=False)

    @staticmethod
    def pool_close_fds():
        HidrawWriter.fd.close()

    @staticmethod
    def sigalrm_handler(signum, frame):
        raise TimeoutError

    @staticmethod
    def pool_write(data, timeout):
        timedout = False
        oserror = False

        try:
            if timeout != None:
                old_sigalrm_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, HidrawWriter.sigalrm_handler)
                signal.setitimer(signal.ITIMER_REAL, timeout)

            HidrawWriter.fd.write(data)
        except TimeoutError:
            pass
        except OSError:
            pass

        finally:
            if timeout != None:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_sigalrm_handler)

    def write(self, data, timeout = None):
        return self.write_pool.apply(HidrawWriter.pool_write, (data, timeout))

    def close(self):
        self.write_pool.apply(HidrawWriter.pool_close_fds)
        self.write_pool.close()
        self.write_pool.join()


class HidrawDS4Device(DS4Device):
    def __init__(self, name, addr, type, hidraw_device, event_device):
        try:
            self.hidraw_writer = HidrawWriter(hidraw_device)
            self.report_fd = os.open(hidraw_device, os.O_RDWR | os.O_NONBLOCK)
            self.fd = FileIO(self.report_fd, "rb+", closefd=False)

            self.input_device = InputDevice(event_device)
            self.input_device.grab()
        except (OSError, IOError) as err:
            raise DeviceError(err)

        self.buf = bytearray(self.report_size)

        super(HidrawDS4Device, self).__init__(name, addr, type)

    def read_report(self):
        try:
            ret = self.fd.readinto(self.buf)
        except IOError:
            return

        # Disconnection
        if ret == 0:
            return

        # Invalid report size or id, just ignore it
        if ret < self.report_size or self.buf[0] != self.valid_report_id:
            return False

        if self.type == "bluetooth":
            # Cut off bluetooth data
            buf = zero_copy_slice(self.buf, 2)
        else:
            buf = self.buf

        return self.parse_report(buf)

    def read_feature_report(self, report_id, size):
        op = HIDIOCGFEATURE(size + 1)
        buf = bytearray(size + 1)
        buf[0] = report_id

        return fcntl.ioctl(self.fd, op, bytes(buf))


    def write_report(self, report_id, data, timeout = None):
        try:
            hid = bytearray((report_id,))
            self.hidraw_writer.write(hid + data, timeout)
        except TimeoutError:
            pass


    def close(self):
        try:
            self.hidraw_writer.close()
            self.fd.close()
            self.input_device.ungrab()
        except IOError:
            pass


class HidrawBluetoothDS4Device(HidrawDS4Device):
    __type__ = "bluetooth"

    report_size = 78
    valid_report_id = 0x11

    audio_buffer_size = 448
    audio_buffer = b''
    frame_number = 0

    def set_operational(self):
        self.read_feature_report(0x02, 37)

    def increment_frame_number(self, inc):
            self.frame_number += inc
            if self.frame_number > 0xffff:
                    self.frame_number = 0

    def play_audio(self, headers, data):
        if len(self.audio_buffer) + len(data) <= self.audio_buffer_size:
            self.audio_buffer += data
            return

        crc = b'\x00\x00\x00\x00'
        audio_header = b'\x24'

        self.increment_frame_number(4)

        report_id = 0x17
        report = (
            b'\x40\xA0'
            + struct.pack("<H", self.frame_number)
            + audio_header
            + self.audio_buffer
            + bytearray(452 - len(self.audio_buffer)) + crc
        )

        self.audio_buffer = data

        if self._volume_r == 0:
            self.set_volume(60, 60, 0)
            self._control()

        maxtime = 0.01*self.audio_buffer_size/headers.calculate_bit_rate()
        self.write_report(report_id, report, timeout = maxtime)


class HidrawUSBDS4Device(HidrawDS4Device):
    __type__ = "usb"

    report_size = 64
    valid_report_id = 0x01

    def set_operational(self):
        # Get the bluetooth MAC
        addr = self.read_feature_report(0x81, 6)[1:]
        addr = ["{0:02x}".format(c) for c in bytearray(addr)]
        addr = ":".join(reversed(addr)).upper()

        self.device_name = "{0} {1}".format(addr, self.device_name)
        self.device_addr = addr


HID_DEVICES = {
    "Sony Computer Entertainment Wireless Controller": HidrawUSBDS4Device,
    "Wireless Controller": HidrawBluetoothDS4Device,
}


class HidrawBackend(Backend):
    __name__ = "hidraw"

    def setup(self):
        pass

    def _get_future_devices(self, context):
        """Return a generator yielding new devices."""
        monitor = Monitor.from_netlink(context)
        monitor.filter_by("hidraw")
        monitor.start()

        self._scanning_log_message()
        for device in iter(monitor.poll, None):
            if device.action == "add":
                # Sometimes udev rules has not been applied at this point,
                # causing permission denied error if we are running in user
                # mode. With this sleep this will hopefully not happen.
                sleep(1)

                yield device
                self._scanning_log_message()

    def _scanning_log_message(self):
        self.logger.info("Scanning for devices")

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        context = Context()

        existing_devices = context.list_devices(subsystem="hidraw")
        future_devices = self._get_future_devices(context)

        for hidraw_device in itertools.chain(existing_devices, future_devices):
            hid_device = hidraw_device.parent
            if hid_device.subsystem != "hid":
                continue

            cls = HID_DEVICES.get(hid_device.get("HID_NAME"))
            if not cls:
                continue

            for child in hid_device.parent.children:
                event_device = child.get("DEVNAME", "")
                if event_device.startswith("/dev/input/event"):
                    break
            else:
                continue


            try:
                device_addr = hid_device.get("HID_UNIQ", "").upper()
                if device_addr:
                    device_name = "{0} {1}".format(device_addr,
                                                   hidraw_device.sys_name)
                else:
                    device_name = hidraw_device.sys_name

                yield cls(name=device_name,
                          addr=device_addr,
                          type=cls.__type__,
                          hidraw_device=hidraw_device.device_node,
                          event_device=event_device)

            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}", err)
