import sys

from .device import DS4Report


VALID_BUTTONS = DS4Report._fields


def parse_button_combo(combo):
    def button_prefix(button):
        button = button.strip()
        if button in ("up", "down", "left", "right"):
            prefix = "dpad_"
        else:
            prefix = "button_"

        if prefix + button not in VALID_BUTTONS:
            raise ValueError("Invalid button: {0}".format(button))

        return prefix + button

    return tuple(map(button_prefix, combo.lower().split("+")))


def zero_copy_slice(buf, start=None, end=None):
    # No need for an extra copy on Python 3.3+
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        buf = memoryview(buf)

    return buf[start:end]
