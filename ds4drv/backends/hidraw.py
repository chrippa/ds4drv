"""Just a small stub to test USB hidraw."""

from time import sleep

from ..backend import Backend
from ..exceptions import DeviceError
from ..device import DS4Device


REPORT_SIZE = 64


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

        return self.parse_report(self.buf)

    def write_report(self, report_id, data):
        hid = bytearray((report_id,))

        self.fd.write(hid + data)

    def close(self):
        self.fd.close()


DEVICES = ["/dev/hidraw5"]

class HidrawBackend(Backend):
    __name__ = "hidraw"

    def setup(self):
        pass

    def find_device(self):
        try:
            d = DEVICES.pop(0)
            return HidrawDS4Device.open(d, "usb", d)
        except IndexError:
            pass

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        while True:
            try:
                device = self.find_device()
                if device:
                    yield device
            except DeviceError as err:
                self.logger.error("Unable to open DS4 device: {0}",
                                  err)

            sleep(1)
