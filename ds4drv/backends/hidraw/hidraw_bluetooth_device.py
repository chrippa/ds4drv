from .hidraw_device import HidrawDS4Device
from ...utils import zero_copy_slice


REPORT_SIZE = 78


class HidrawBluetoothDS4Device(HidrawDS4Device):
    @staticmethod
    def hid_name():
        return "Wireless Controller"

    def __init__(self, hidraw_device, type, addr, sys_name):
        device_name = addr + " " + sys_name

        super(HidrawBluetoothDS4Device, self).__init__(hidraw_device, type, device_name, REPORT_SIZE)

    def get_trimmed_report_data(self):
        # Cut off bluetooth data
        return zero_copy_slice(self.buf, 2)
