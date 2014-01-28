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

    def _get_future_devices(self, context):
        """Return a generator yielding new devices."""
        monitor = Monitor.from_netlink(context)
        monitor.filter_by('hidraw')
        monitor.start()

        self._scanning_log_message()
        for device in iter(monitor.poll, None):
            if device.action == 'add':
                yield device
                self._scanning_log_message()

    def _scanning_log_message(self):
        self.logger.info("Scanning for devices")

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        context = Context()

        existing_devices = context.list_devices(subsystem='hidraw')
        future_devices = self._get_future_devices(context)

        for hidraw_device in itertools.chain(existing_devices, future_devices):
            udev_device = hidraw_device.parent

            if udev_device.subsystem != 'hid':
                continue

            try:
                if udev_device['HID_NAME'] == HidrawBluetoothDS4Device.hid_name():
                    yield HidrawBluetoothDS4Device(hidraw_device.device_node, 'bluetooth',
                                                   udev_device['HID_UNIQ'], hidraw_device.sys_name)
                elif udev_device['HID_NAME'] == HidrawUSBDS4Device.hid_name():
                    yield HidrawUSBDS4Device(hidraw_device.device_node, 'usb',
                                             hidraw_device.sys_name)
            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}", err)
