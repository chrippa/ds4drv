import sys

from .device import DS4Report


VALID_BUTTONS = DS4Report.__slots__


def iter_except(func, exception, first=None):
    """Call a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like __builtin__.iter(func, sentinel) but uses an exception instead
    of a sentinel to end the loop.
    """
    try:
        if first is not None:
            yield first()
        while True:
            yield func()
    except exception:
        pass


def parse_button_combo(combo, sep="+"):
    def button_prefix(button):
        button = button.strip()
        if button in ("up", "down", "left", "right"):
            prefix = "dpad_"
        else:
            prefix = "button_"

        if prefix + button not in VALID_BUTTONS:
            raise ValueError("Invalid button: {0}".format(button))

        return prefix + button

    return tuple(map(button_prefix, combo.lower().split(sep)))


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})


def zero_copy_slice(buf, start=None, end=None):
    # No need for an extra copy on Python 3.3+
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        buf = memoryview(buf)

    return buf[start:end]
