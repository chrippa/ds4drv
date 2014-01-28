import sys

from ...exceptions import DeviceError
from ...device import DS4Device


class HidrawDS4Device(DS4Device):
    @classmethod
    def open(cls, name, type, hidraw):
        try:
            fd = open(hidraw, "rb+", 0)
        except OSError as err:
            raise DeviceError(err)

        return cls(name, type, fd)

    def __init__(self, name, type, fd, report_size):
        self.fd = fd
        self.report_size = report_size
        self.buf = bytearray(self.report_size)

        super(HidrawDS4Device, self).__init__(name, type)

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
        hid = bytearray((report_id,))

        self.fd.write(hid + data)

    def close(self):
        self.fd.close()
