import socket
import subprocess

from ..backend import Backend
from ..exceptions import BackendError, DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice


L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_SET_REPORT = 0x50
HIDP_DATA_RTYPE_OUTPUT  = 0x02

REPORT_ID = 0x11
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
            int_socket.setblocking(False)
        except socket.error as err:
            DeviceError("Failed to connect: {0}".format(err))

        return cls(addr, ctl_socket, int_socket)

    def __init__(self, addr, ctl_sock, int_sock):
        self.buf = bytearray(REPORT_SIZE)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock
        self.report_fd = int_sock.fileno()

        super(BluetoothDS4Device, self).__init__(addr.upper(), addr,
                                                 "bluetooth")

    def read_report(self):
        try:
            ret = self.int_sock.recv_into(self.buf)
        except IOError:
            return

        # Disconnection
        if ret == 0:
            return

        # Invalid report size or id, just ignore it
        if ret < REPORT_SIZE or self.buf[1] != REPORT_ID:
            return False

        # Cut off bluetooth data
        buf = zero_copy_slice(self.buf, 3)

        return self.parse_report(buf)

    def write_report(self, report_id, data):
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT,
                         report_id))

        self.ctl_sock.sendall(hid + data)

    def set_operational(self):
        try:
            self.set_led(255, 255, 255)
        except socket.error as err:
            raise DeviceError("Failed to set operational mode: {0}".format(err))

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
        try:
            res = subprocess.check_output(["hcitool", "scan", "--flush"],
                                          stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
             raise BackendError("'hcitool scan' returned error. Make sure "
                                "your bluetooth device is powered up with "
                                "'hciconfig hciX up'.")

        devices = []
        res = res.splitlines()[1:]
        for _, bdaddr, name in map(lambda l: l.split(b"\t"), res):
            devices.append((bdaddr.decode("utf8"), name.decode("utf8")))

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
            except BackendError as err:
                self.logger.error("Error while scanning for devices: {0}",
                                  err)
                return
            except DeviceError as err:
                self.logger.error("Unable to connect to detected device: {0}",
                                  err)

