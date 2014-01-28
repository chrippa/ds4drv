import itertools
from pyudev import Context, Monitor

from ...backend import Backend
from ...exceptions import DeviceError
from .hidraw_bluetooth_device import HidrawBluetoothDS4Device
from .hidraw_usb_device import HidrawUSBDS4Device


class HidrawBackend(Backend):
    __name__ = "hidraw"

    def setup(self):
        pass

    def get_future_devices(self, context):
        """Return a generator yielding new devices."""
        monitor = Monitor.from_netlink(context)
        monitor.filter_by('hidraw')
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

        existing_devices = context.list_devices(subsystem='hidraw')
        future_devices = self.get_future_devices(context)

        for hidraw_device in itertools.chain(existing_devices, future_devices):
            udev_device = hidraw_device.parent

            if udev_device.subsystem != 'hid':
                continue

            try:
                if udev_device['HID_NAME'] == HidrawBluetoothDS4Device.get_hid_name():
                    name = 'Bluetooth Controller (' + udev_device['HID_UNIQ'] + ' ' + hidraw_device.sys_name + ')'
                    yield HidrawBluetoothDS4Device.open(name, 'bluetooth', hidraw_device.device_node)
                elif udev_device['HID_NAME'] == HidrawUSBDS4Device.get_hid_name():
                    name = 'USB Controller (' + hidraw_device.sys_name + ')'
                    yield HidrawUSBDS4Device.open(name, 'usb', hidraw_device.device_node)
            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}", err)
