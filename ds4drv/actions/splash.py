from ..action import Action

from collections import namedtuple
from time import sleep


Action.add_option("--no-splash", action="store_true",
                  help="Disable rumbling controller and flashing LEDs on connection.")


class ActionSplash(Action):
    """Rumble controller and flash LEDs on connection."""

    def __init__(self, *args, **kwargs):
        super(ActionSplash, self).__init__(*args, **kwargs)

        self.led = (0, 0, 1)
        self.no_splash = False

    @staticmethod
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

    def setup(self, device):
        if self.no_splash == True:
            return

        splash_time = 0.5

        # Define key frames
        high_rumble = (255, 63) # (small_rumble, big_rumble)
        low_rumble  = (0, 0)

        Frame = namedtuple('Frame', ['led', 'rumble'])

        splash_key_frames = [
            Frame(led = self.led,      rumble = high_rumble),
            Frame(led = (255, 255, 0), rumble = low_rumble),
            Frame(led = (0, 255, 255), rumble = high_rumble),
            Frame(led = (0, 0, 0),     rumble = low_rumble),
            Frame(led = self.led,      rumble = low_rumble)
        ]
        splash_frame_counts = [4, 6, 8, 4]


        # Build all frames
        splash_frames = []
        for i, nframes in enumerate(splash_frame_counts):
            frame_leds = self.interpolate_leds(
                splash_key_frames[i].led, splash_key_frames[i+1].led,
                nframes
            )
            frame_rumbles = [splash_key_frames[i].rumble] * nframes

            for led, rumble in zip(frame_leds, frame_rumbles):
                splash_frames.append(Frame(led = led, rumble = rumble))


        # Play frames
        splash_frame_duration = splash_time/len(splash_frames)

        for splash_frame in splash_frames:
            frame_led    = tuple(map(int, splash_frame.led))
            frame_rumble = tuple(map(int, splash_frame.rumble))

            self.controller.device.set_led(*frame_led)
            self.controller.device.rumble(*frame_rumble)

            sleep(splash_frame_duration)

        self.controller.device.set_led(*(self.led))

    def load_options(self, options):
        self.led = options.led
        self.no_splash = options.no_splash
