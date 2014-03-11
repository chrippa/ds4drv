from ..action import Action
from ..config import hexcolor

Action.add_option("--led", metavar="color", default="0000ff", type=hexcolor,
                  help="Sets color of the LED. Uses hex color codes, "
                       "e.g. 'ff0000' is red. Default is '0000ff' (blue)")


class ActionLED(Action):
    """Sets the LED color on the device."""

    def setup(self, device):
        device.set_led(*self.controller.options.led)

    def load_options(self, options):
        if self.controller.device:
            self.controller.device.set_led(*options.led)
