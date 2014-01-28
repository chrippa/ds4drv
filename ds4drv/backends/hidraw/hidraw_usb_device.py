from .hidraw_device import HidrawDS4Device


REPORT_SIZE = 64


class HidrawUSBDS4Device(HidrawDS4Device):
    @staticmethod
    def hid_name():
        return "Sony Computer Entertainment Wireless Controller"

    def __init__(self, hidraw_device, type, sys_name):
        super(HidrawUSBDS4Device, self).__init__(hidraw_device, type, sys_name, REPORT_SIZE)

    def get_trimmed_report_data(self):
        return self.buf
