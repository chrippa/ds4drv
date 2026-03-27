import sys
import signal

from threading import Thread, Event

from .actions import ActionRegistry
from .backends import BluetoothBackend, HidrawBackend
from .config import load_options
from .daemon import Daemon
from .eventloop import EventLoop
from .exceptions import BackendError


class DS4Controller(object):
    def __init__(self, index, options, dynamic=False, disconnect_device_event=None):
        self.index = index
        self.dynamic = dynamic
        self.logger = Daemon.logger.new_module("controller {0}".format(index))

        self.error = None
        self.device = None
        self.loop = EventLoop()
        self.disconnect_device_event = disconnect_device_event

        self.actions = [cls(self) for cls in ActionRegistry.actions]
        self.bindings = options.parent.bindings
        self.current_profile = "default"
        self.default_profile = options
        self.options = self.default_profile
        self.profiles = options.profiles
        self.profile_options = dict(options.parent.profiles)
        self.profile_options["default"] = self.default_profile

        if self.profiles:
            self.profiles.append("default")

        self.load_options(self.options)

    def fire_event(self, event, *args):
        self.loop.fire_event(event, *args)

    def load_profile(self, profile):
        if profile == self.current_profile:
            return

        profile_options = self.profile_options.get(profile)
        if profile_options:
            self.logger.info("Switching to profile: {0}", profile)
            self.load_options(profile_options)
            self.current_profile = profile
            self.fire_event("load-profile", profile)
        else:
            self.logger.warning("Ignoring invalid profile: {0}", profile)

    def next_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) + 1
        if next_index >= len(self.profiles):
            next_index = 0

        self.load_profile(self.profiles[next_index])

    def prev_profile(self):
        if not self.profiles:
            return

        next_index = self.profiles.index(self.current_profile) - 1
        if next_index < 0:
            next_index = len(self.profiles) - 1

        self.load_profile(self.profiles[next_index])

    def setup_device(self, device):
        self.logger.info("Connected to {0}", device.name)

        self.device = device
        self.device.set_led(*self.options.led)
        self.fire_event("device-setup", device)
        self.loop.add_watcher(device.report_fd, self.read_report)
        self.load_options(self.options)

    def cleanup_device(self):
        self.logger.info("Disconnected")
        self.fire_event("device-cleanup")
        self.loop.remove_watcher(self.device.report_fd)
        self.device.close()
        self.device = None

        # Tell main thread one device was disconnected, maybe he can now connect another controller
        if self.disconnect_device_event:
            self.logger.debug("Telling main thread a device was disconnected")
            self.disconnect_device_event.set()
            self.disconnect_device_event.clear()

        if self.dynamic:
            self.loop.stop()

    def load_options(self, options):
        self.fire_event("load-options", options)
        self.options = options

    def read_report(self):
        report = self.device.read_report()

        if not report:
            if report is False:
                return

            self.cleanup_device()
            return

        self.fire_event("device-report", report)

    def run(self):
        self.loop.run()

    def exit(self, *args, **kwargs):
        error = kwargs.pop('error', True)

        if self.device:
            self.cleanup_device()

        if error == True:
            self.logger.error(*args)
            self.error = True
        else:
            self.logger.info(*args)


def create_controller_thread(index, controller_options, dynamic=False, disconnect_device_event=None):
    controller = DS4Controller(index, controller_options, dynamic=dynamic,
                               disconnect_device_event=disconnect_device_event)

    thread = Thread(target=controller.run)
    thread.controller = controller
    thread.start()

    return thread


class SigintHandler(object):
    def __init__(self, threads):
        self.threads = threads

    def cleanup_controller_threads(self):
        for thread in self.threads:
            thread.controller.exit("Cleaning up...", error=False)
            thread.controller.loop.stop()
            thread.join()

    def __call__(self, signum, frame):
        signal.signal(signum, signal.SIG_DFL)

        self.cleanup_controller_threads()
        sys.exit(0)


def main():
    threads = []

    sigint_handler = SigintHandler(threads)
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        options = load_options()
    except ValueError as err:
        Daemon.exit("Failed to parse options: {0}", err)

    if options.hidraw:
        backend = HidrawBackend(Daemon.logger)
    else:
        backend = BluetoothBackend(Daemon.logger)

    disconnect_device_event = None  # By default, no event needed if we don't limit number of simultaneous devices
    # We want to limit the number of simultaneous connected controllers
    if options.controller_limit and options.controller_limit > 0:
        disconnect_device_event = Event()  # This event is used to tell the main loop that one device is disconnected

    try:
        backend.setup()
    except BackendError as err:
        Daemon.exit(err)

    if options.daemon:
        Daemon.fork(options.daemon_log, options.daemon_pid)

    for index, controller_options in enumerate(options.controllers):
        thread = create_controller_thread(index + 1, controller_options, disconnect_device_event=disconnect_device_event)
        threads.append(thread)

    for device in backend.devices:
        connected_devices = []
        for thread in threads:
            # Controller has received a fatal error, exit
            if thread.controller.error:
                sys.exit(1)

            if thread.controller.device:
                connected_devices.append(thread.controller.device.device_addr)

            # Clean up dynamic threads
            if not thread.is_alive():
                threads.remove(thread)

        if device.device_addr in connected_devices:
            backend.logger.warning("Ignoring already connected device: {0}",
                                   device.device_addr)
            continue

        for thread in filter(lambda t: not t.controller.device, threads):
            break
        else:
            thread = create_controller_thread(len(threads) + 1,
                                              options.default_controller,
                                              dynamic=True,
                                              disconnect_device_event=disconnect_device_event)
            threads.append(thread)

        thread.controller.setup_device(device)
        connected_devices.append(device)

        if options.controller_limit and len(connected_devices) >= options.controller_limit:
            # We have reached the defined controller limit, we now need to wait until a device is disconnected
            disconnect_device_event.wait()

if __name__ == "__main__":
    main()
