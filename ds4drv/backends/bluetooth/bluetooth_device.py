import socket

from ...exceptions import DeviceError
from ...device import DS4Device
from ...utils import zero_copy_slice

L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_SET_REPORT = 0x50
HIDP_DATA_RTYPE_OUTPUT  = 0x02

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

    def __init__(self, addr, ctl_sock, int_sock):
        self.buf = bytearray(REPORT_SIZE)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock

        super(BluetoothDS4Device, self).__init__(addr, "bluetooth")

    def read_report(self):
        ret = self.int_sock.recv_into(self.buf)

        # Disconnection
        if ret == 0:
            return

        # Invalid report size, just ignore it
        if ret < REPORT_SIZE:
            return False

        # Cut off bluetooth data
        buf = zero_copy_slice(self.buf, 3)

        return self.parse_report(buf)

    def write_report(self, report_id, data):
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT,
                         report_id))

        self.ctl_sock.sendall(hid + data)

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()
