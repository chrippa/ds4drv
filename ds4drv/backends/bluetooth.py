import socket
import dbus
import time

from ..backend import Backend
from ..exceptions import BackendError, DeviceError
from ..device import DS4Device
from ..utils import zero_copy_slice

BLUEZ_SERVICE = "org.bluez"
DBUS_OM = "org.freedesktop.DBus.ObjectManager"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

L2CAP_PSM_HIDP_CTRL = 0x11
L2CAP_PSM_HIDP_INTR = 0x13

HIDP_TRANS_SET_REPORT = 0x50
HIDP_DATA_RTYPE_OUTPUT = 0x02

REPORT_ID = 0x11
REPORT_SIZE = 79


class BluetoothDS4Device(DS4Device):
    @classmethod
    def connect(cls, addr):
            ctl = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
            )

            intr = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
            )

            ctl.connect((addr, L2CAP_PSM_HIDP_CTRL))
            intr.connect((addr, L2CAP_PSM_HIDP_INTR))
            intr.setblocking(False)

            return cls(addr, ctl, intr)

        except socket.error as e:
            raise DeviceError(f"Failed to connect: {e}")

    def __init__(self, addr, ctl_sock, int_sock):
        self.buf = bytearray(REPORT_SIZE)
        self.ctl_sock = ctl_sock
        self.int_sock = int_sock
        self.report_fd = int_sock.fileno()

        super().__init__(addr.upper(), addr, "bluetooth")

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
        hid = bytearray((HIDP_TRANS_SET_REPORT | HIDP_DATA_RTYPE_OUTPUT, report_id))

        self.ctl_sock.sendall(hid + data)

    def set_operational(self):
        try:
            self.set_led(255, 255, 255)
        except socket.error as err:
            raise DeviceError(f"Failed to set operational mode: {err}")

    def close(self):
        self.int_sock.close()
        self.ctl_sock.close()


class BluetoothBackend(Backend):
    __name__ = "bluetooth"

    def __init__(self, logger):
        super().__init__(logger)
        self.connected = set()

    # ---------------------------
    # DBUS helpers
    # ---------------------------

    def _bus(self):
        return dbus.SystemBus()

    def _om(self):
        bus = self._bus()
        obj = bus.get_object(BLUEZ_SERVICE, "/")
        return dbus.Interface(obj, DBUS_OM)

    def _get_adapter_path(self):
        om = self._om()
        objects = om.GetManagedObjects()

        adapters = []

        for path, ifaces in objects.items():
            if ADAPTER_IFACE in ifaces:
                adapters.append(path)

        if not adapters:
            raise BackendError("No Bluetooth adapter found")

        return adapters[0]

    def _props(self, path):
        bus = self._bus()
        obj = bus.get_object(BLUEZ_SERVICE, path)
        return dbus.Interface(obj, dbus.PROPERTIES_IFACE)

    # ---------------------------
    # setup
    # ---------------------------

     def setup(self):
        """Check if the bluetooth controller is available."""
         try:
            path = self._get_adapter_path()
            props = self._props(path)

            powered = props.Get(ADAPTER_IFACE, "Powered")

            if not powered:
                raise BackendError("Bluetooth adapter is powered off")

        except Exception as e:
            raise BackendError(f"Bluetooth setup failed: {e}")

    # ---------------------------
    # scan
    # ---------------------------

    def scan(self):
        """Scan for bluetooth devices."""
        bus = self._bus()
        om = self._om()

        adapter_path = self._get_adapter_path()
        adapter = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE, adapter_path), ADAPTER_IFACE
        )

        try:
            adapter.StartDiscovery()
            time.sleep(3)
            adapter.StopDiscovery()
        except Exception:
            pass

        devices = []
        objects = om.GetManagedObjects()

        for _, ifaces in objects.items():
            dev = ifaces.get(DEVICE_IFACE)
            if not dev:
                continue

            addr = dev.get("Address")
            name = dev.get("Alias") or dev.get("Name") or ""

            if addr:
                devices.append((str(addr), str(name)))

         return devices

    # ---------------------------
    # device discovery
    # ---------------------------

    def find_device(self):
        """Scan for bluetooth devices and return a DS4 device if found."""
        for addr, name in self.scan():
            name_u = (name or "").upper()

            if (
                "WIRELESS CONTROLLER" in name_u
                or "DUALSHOCK" in name_u
                or "DUALSENSE" in name_u
            ):
                if addr in self.connected:
                    continue

                self.logger.info(f"Found DS controller: {addr}")

                try:
                    dev = BluetoothDS4Device.connect(addr)
                    self.connected.add(addr)
                    return dev
                except Exception as e:
                    self.logger.error(f"Failed to connect {addr}: {e}")
                    continue

        return None

    # ---------------------------
    # main loop
    # ---------------------------

    @property
    def devices(self):
        """Wait for new DS4 devices to appear."""
        log_msg = True

        while True:
            try:
                if log_msg:
                    self.logger.info("Scanning for DS4 devices (BlueZ DBus)")

                dev = self.find_device()

                if dev:
                    yield dev
                    log_msg = True
                else:
                    log_msg = False

                time.sleep(2)

            except BackendError as e:
                self.logger.error(str(e))
                return
            except DeviceError as e:
                self.connected.clear()
                self.logger.error(str(e))

