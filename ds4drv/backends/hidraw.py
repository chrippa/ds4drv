import sys
import itertools
from pyudev import Context, Monitor

from ..backend import Backend
from ..exceptions import DeviceError
from ..device import DS4Device


REPORT_SIZE = 78


class HidrawDS4Device(DS4Device):
    @classmethod
    def open(cls, name, type, hidraw):
        try:
            fd = open(hidraw, "rb+", 0)
        except OSError as err:
            raise DeviceError(err)

        return cls(name, type, fd)

    def __init__(self, name, type, fd):
        self.fd = fd
        self.buf = bytearray(REPORT_SIZE)

        super(HidrawDS4Device, self).__init__(name, type)

    def read_report(self):
        ret = self.fd.readinto(self.buf)

        # Disconnection
        if ret == 0:
            return

        # Invalid report size, just ignore it
        if ret < REPORT_SIZE:
            return False

        # No need for a extra copy on Python 3.3+
        if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
            buf = memoryview(self.buf)
        else:
            buf = self.buf

        # Cut off bluetooth data
        buf = self.buf[2:]

        return self.parse_report(buf)

    def write_report(self, report_id, data):
        hid = bytearray((report_id,))

        self.fd.write(hid + data)

    def close(self):
        self.fd.close()


class HidrawBackend(Backend):
    __name__ = "hidraw"

    def setup(self):
        pass

    def get_future_devices(self, context):
        """Return a generator yielding new devices."""
        monitor = Monitor.from_netlink(context)
        monitor.filter_by('hid')
        monitor.start()

        self.scanning_log_message()
        for device in iter(monitor.poll, None):
            if device.action == 'add':
                yield device
                self.scanning_log_message()

    def scanning_log_message(self):
        self.logger.info("Scanning for devices")

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        context = Context()

        existing_devices = context.list_devices(subsystem='hid')
        future_devices = self.get_future_devices(context)

        for udev_device in itertools.chain(existing_devices, future_devices):
            if udev_device['HID_NAME'] == 'Wireless Controller':
                for child in udev_device.children:
                    if child.subsystem == 'hidraw':
                        name = udev_device['HID_UNIQ'] + ' (' + child.sys_name + ')'
                        try:
                            yield HidrawDS4Device.open(name, "bluetooth", child.device_node)
                        except DeviceError as err:
                            self.logger.error("Unable to open DS4 device: {0}", err)
