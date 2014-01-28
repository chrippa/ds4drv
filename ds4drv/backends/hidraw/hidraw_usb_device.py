from .hidraw_device import HidrawDS4Device


REPORT_SIZE = 64


class HidrawUSBDS4Device(HidrawDS4Device):
    def get_hid_name():
        return 'Sony Computer Entertainment Wireless Controller'

    def __init__(self, name, type, fd):
        super(HidrawUSBDS4Device, self).__init__(name, type, fd, REPORT_SIZE)

    def get_trimmed_report_data(self):
        return self.buf
