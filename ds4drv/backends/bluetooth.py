import socket
import sys
import subprocess

from ..backend import Backend
from ..exceptions import BackendError, DeviceError
from ..device import DS4Device

L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_GET_REPORT = 0x40
HIDP_TRANS_SET_REPORT = 0x50

HIDP_DATA_RTYPE_INPUT   = 0x01
HIDP_DATA_RTYPE_OUTPUT  = 0x02
HIDP_DATA_RTYPE_FEATURE = 0x03

REPORT_SIZE = 79


class BluetoothDS4Device(DS4Device):
    @classmethod
    def connect(cls, addr):
        ctl_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        int_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET,
                                   socket.BTPROTO_L2CAP)

        try:
            ctl_socket.connect((addr, L2CAP_PSM_HIDP_CTRL))
            int_socket.connect((addr, L2CAP_PSM_HIDP_INTR))
        except socket.error as err:
            DeviceError("Failed to connect: {0}".format(err))

        return cls(addr, ctl_socket, int_socket)

    def __init__(self, name, ctl_sock, int_sock):
        self.buf = bytearray(REPORT_SIZE)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock

        super(BluetoothDS4Device, self).__init__(name, "bluetooth")

    def read_report(self):
        ret = self.int_sock.recv_into(self.buf)

        # Disconnection
        if ret == 0:
            return

        # Invalid report size, just ignore it
        if ret < REPORT_SIZE:
            return False

        # No need for a extra copy on Python 3.3+
        if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
            buf = memoryview(self.buf)
        else:
            buf = self.buf

        # Cut off bluetooth data
        buf = buf[3:]

        return self.parse_report(buf)

    def write_report(self, report_id, data):
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT,
                         report_id))

        self.ctl_sock.sendall(hid + data)

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()


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
