import sys

from .hidraw_device import HidrawDS4Device


REPORT_SIZE = 78


class HidrawBluetoothDS4Device(HidrawDS4Device):
    def get_hid_name():
        return 'Wireless Controller'

    def __init__(self, hidraw_device, type, addr, sys_name):
        device_name = addr + ' ' + sys_name

        super(HidrawBluetoothDS4Device, self).__init__(hidraw_device, type, device_name, REPORT_SIZE)

    def get_trimmed_report_data(self):
        # No need for a extra copy on Python 3.3+
        if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
            buf = memoryview(self.buf)
        else:
            buf = self.buf

        # Cut off bluetooth data
        return buf[2:]
