import fcntl
import itertools

from evdev import InputDevice
from pyudev import Context, Monitor
from time import sleep

from ..backend import Backend
from ..exceptions import DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice


HIDIOCGFEATURE_38 = 3223734279


class HidrawDS4Device(DS4Device):
    def __init__(self, hidraw_device, event_device, type, device_name):
        try:
            self.fd = open(hidraw_device, "rb+", 0)
            self.input_device = InputDevice(event_device)
            self.input_device.grab()
        except (OSError, IOError) as err:
            raise DeviceError(err)

        self.buf = bytearray(self.report_size)

        super(HidrawDS4Device, self).__init__(device_name, type)

    def read_report(self):
        ret = self.fd.readinto(self.buf)

        # Disconnection
        if ret == 0:
            return

        # Invalid report size, just ignore it
        if ret < self.report_size:
            return False

        buf = self.get_trimmed_report_data()

        return self.parse_report(buf)

    def get_trimmed_report_data(self):
        raise NotImplementedError

    def write_report(self, report_id, data):
        if self.type == "bluetooth":
            # TODO: Add a check for a kernel that supports writing
            # output reports when such a kernel has been released.
            return

        hid = bytearray((report_id,))
        self.fd.write(hid + data)

    def close(self):
        try:
            self.fd.close()
            self.input_device.ungrab()
        except IOError:
            pass

    @property
    def report_size(self):
        raise NotImplementedError


class HidrawBluetoothDS4Device(HidrawDS4Device):
    @staticmethod
    def hid_name():
        return "Wireless Controller"

    def __init__(self, hidraw_device, event_device, type, addr, sys_name):
        device_name = "{0} {1}".format(addr, sys_name)

        super(HidrawBluetoothDS4Device, self).__init__(hidraw_device,
                                                       event_device, type,
                                                       device_name)

    def get_trimmed_report_data(self):
        # Cut off bluetooth data
        return zero_copy_slice(self.buf, 2)

    def set_operational(self):
        try:
            buf = bytearray(38)
            buf[0] = 0x2
            fcntl.ioctl(self.fd, HIDIOCGFEATURE_38, bytes(buf))
        except IOError:
            pass

    @property
    def report_size(self):
        return 78


class HidrawUSBDS4Device(HidrawDS4Device):
    @staticmethod
    def hid_name():
        return "Sony Computer Entertainment Wireless Controller"

    def __init__(self, hidraw_device, event_device, type, sys_name):
        super(HidrawUSBDS4Device, self).__init__(hidraw_device, event_device,
                                                 type, sys_name)

    def get_trimmed_report_data(self):
        return self.buf

    def set_operational(self):
        self.set_led(255, 255, 255)

    @property
    def report_size(self):
        return 64


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

            if hid_device["HID_NAME"] not in (HidrawBluetoothDS4Device.hid_name(),
                                              HidrawUSBDS4Device.hid_name()):
                continue

            for child in hid_device.parent.children:
                event_device = child.get("DEVNAME", "")
                if event_device.startswith("/dev/input/event"):
                    break
            else:
                continue

            try:
                if hid_device["HID_NAME"] == HidrawBluetoothDS4Device.hid_name():
                    yield HidrawBluetoothDS4Device(hidraw_device.device_node,
                                                   event_device, "bluetooth",
                                                   hid_device["HID_UNIQ"],
                                                   hidraw_device.sys_name)
                elif hid_device["HID_NAME"] == HidrawUSBDS4Device.hid_name():
                    yield HidrawUSBDS4Device(hidraw_device.device_node,
                                             event_device, "usb",
                                             hidraw_device.sys_name)
            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}", err)
