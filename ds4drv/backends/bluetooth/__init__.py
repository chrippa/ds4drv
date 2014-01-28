import subprocess

from ...backend import Backend
from ...exceptions import BackendError, DeviceError
from .bluetooth_device import BluetoothDS4Device


class BluetoothBackend(Backend):
    __name__ = "bluetooth"

    def setup(self):
        """Check if the bluetooth controller is available."""
        try:
            subprocess.check_output(["hcitool", "clock"],
                                    stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            raise BackendError("'hcitool clock' returned error. Make sure "
                               "your bluetooth device is powered up with "
                               "'hciconfig hciX up'.")
        except OSError:
            raise BackendError("'hcitool' could not be found, make sure you "
                               "have bluez-utils installed.")

    def scan(self):
        """Scan for bluetooth devices."""
        devices = []
        res = subprocess.check_output(["hcitool", "scan", "--flush"],
                                      stderr=subprocess.STDOUT)
        res = res.splitlines()[1:]

        for _, bdaddr, name in map(lambda l: l.split(b"\t"), res):
            devices.append((bdaddr.decode("ascii"), name.decode("ascii")))

        return devices

    def find_device(self):
        """Scan for bluetooth devices and return a DS4 device if found."""
        for bdaddr, name in self.scan():
            if name == "Wireless Controller":
                self.logger.info("Found device {0}", bdaddr)
                return BluetoothDS4Device.connect(bdaddr)

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        log_msg = True
        while True:
            if log_msg:
                self.logger.info("Scanning for devices")

            try:
                device = self.find_device()
                if device:
                    yield device
                    log_msg = True
                else:
                    log_msg = False
            except DeviceError as err:
                self.logger.error("Unable to connect to detected device: {0}",
                                  err)
