import socket
import subprocess

from .daemon import Daemon, BLUETOOTH_LOG
from .device import DS4Device


def bluetooth_check():
    """Check if the bluetooth controller is available."""
    try:
        subprocess.check_output(["hcitool", "clock"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        Daemon.exit("'hcitool clock' returned error. Make sure your "
                    "bluetooth device is on with 'hciconfig hciX up'.")
    except OSError:
        Daemon.exit("'hcitool' could not be found, make sure you have "
                    "bluez-utils installed.")


def bluetooth_scan():
    """Scan for bluetooth devices."""
    devices = []
    res = subprocess.check_output(["hcitool", "scan", "--flush"],
                                  stderr=subprocess.STDOUT)
    res = res.splitlines()[1:]

    for _, bdaddr, name in map(lambda l: l.split(b"\t"), res):
        devices.append((bdaddr.decode("ascii"), name.decode("ascii")))

    return devices


def find_device():
    """Scans for bluetooth devices and returns a DS4 device if found."""
    devices = bluetooth_scan()
    for bdaddr, name in devices:
        if name == "Wireless Controller":
            Daemon.info("Found device {0}", bdaddr,
                        subprefix=BLUETOOTH_LOG)
            return DS4Device.connect(bdaddr)


def find_devices():
    """Scans and yields any DS4 devices found."""
    log_msg = True
    while True:
        if log_msg:
            Daemon.info("Scanning for devices", subprefix=BLUETOOTH_LOG)

        try:
            device = find_device()
            if device:
                yield device
                log_msg = True
            else:
                log_msg = False
        except socket.error as err:
            Daemon.warn("Unable to connect to detected device: {0}", err,
                        subprefix=BLUETOOTH_LOG)
        except subprocess.CalledProcessError:
            Daemon.exit("'hcitool scan' returned error. Make sure your "
                        "bluetooth device is on with 'hciconfig hciX up'.")
        except OSError:
            Daemon.exit("'hcitool' could not be found, make sure you have "
                        "bluez-utils installed.")
