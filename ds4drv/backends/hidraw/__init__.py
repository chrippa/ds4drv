import itertools
from pyudev import Context, Monitor

from ...backend import Backend
from ...exceptions import DeviceError
from .hidraw_bluetooth_device import HidrawBluetoothDS4Device
from .hidraw_usb_device import HidrawUSBDS4Device


HID_NAME_BLUETOOTH = 'Wireless Controller'
HID_NAME_USB = 'Sony Computer Entertainment Wireless Controller'


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
            if udev_device['HID_NAME'] == HID_NAME_BLUETOOTH:
                type = 'bluetooth'
            elif udev_device['HID_NAME'] == HID_NAME_USB:
                type = 'usb'
            else:
                type = None

            if type:
                for child in udev_device.children:
                    if child.subsystem == 'hidraw':
                        try:
                            if type == 'bluetooth':
                                name = 'Bluetooth Controller (' + udev_device['HID_UNIQ'] + ' ' + child.sys_name + ')'
                                yield HidrawBluetoothDS4Device.open(name, type, child.device_node)
                            elif type == 'usb':
                                name = 'USB Controller (' + child.sys_name + ')'
                                yield HidrawUSBDS4Device.open(name, type, child.device_node)
                        except DeviceError as err:
                            self.logger.error("Unable to open DS4 device: {0}", err)
