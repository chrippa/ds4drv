from ..action import Action

from time import sleep


Action.add_option("--no-splash", action="store_true",
                  help="Disable rumbling controller and flashing LEDs on connection.")


class ActionSplash(Action):
    """Rumble controller and flash LEDs on connection."""

    def __init__(self, *args, **kwargs):
        super(ActionSplash, self).__init__(*args, **kwargs)

        self.led = (0, 0, 1)
        self.no_splash = False

    def setup(self, device):
        if self.no_splash == True:
            return

        def interpolate_leds(l1, l2, n):
            diff = (
                (l2[0] - l1[0])/n,
                (l2[1] - l1[1])/n,
                (l2[2] - l1[2])/n
            )
            for i in range(n):
                yield (
                    l1[0] + diff[0]*i,
                    l1[1] + diff[1]*i,
                    l1[2] + diff[2]*i
                )

        splash_time = 1
        splash_frame_counts = [10, 10, 10, 10]
        splash_frame_time = splash_time/sum(splash_frame_counts)

        big_rumble = 255
        small_rumble = 255

        self.controller.device.rumble(small_rumble, big_rumble)
        for led in interpolate_leds(
            self.led, (255, 255, 0), splash_frame_counts[0]
        ):
            self.controller.device.set_led(*tuple(map(int, led)))
            sleep(splash_frame_time)

        self.controller.device.rumble(0, 0)
        for led in interpolate_leds(
            (255, 255, 0), (0, 255, 255), splash_frame_counts[1]
        ):
            self.controller.device.set_led(*tuple(map(int, led)))
            sleep(splash_frame_time)

        self.controller.device.rumble(small_rumble, big_rumble)
        for led in interpolate_leds(
            (0, 255, 255), (0, 0, 0), splash_frame_counts[2]
        ):
            self.controller.device.set_led(*tuple(map(int, led)))
            sleep(splash_frame_time)

        self.controller.device.rumble(0, 0)
        for led in interpolate_leds(
            (0, 0, 0), self.led, splash_frame_counts[2]
        ):
            self.controller.device.set_led(*tuple(map(int, led)))
            sleep(splash_frame_time)

        self.controller.device.set_led(*(self.led))

    def load_options(self, options):
        self.led = options.led
        self.no_splash = options.no_splash
