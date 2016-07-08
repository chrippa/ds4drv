import os.path
import time

from collections import namedtuple

from evdev import UInput, UInputError, ecodes
from evdev import util

from .exceptions import DeviceError

# Check for the existence of a "resolve_ecodes_dict" function.
# Need to know if axis options tuples should be altered.
# This is needed to keep the code compatible with python-evdev < 0.6.0.
absInfoUsesValue = hasattr(util, "resolve_ecodes_dict")

BUTTON_MODIFIERS = ("+", "-")

DEFAULT_A2D_DEADZONE = 50
DEFAULT_AXIS_OPTIONS = (0, 0, 255, 0, 5)
DEFAULT_MOUSE_SENSITIVTY = 0.8
DEFAULT_MOUSE_DEADZONE = 5
DEFAULT_SCROLL_REPEAT_DELAY = .250 # Seconds to wait before continual scrolling
DEFAULT_SCROLL_DELAY = .035        # Seconds to wait between scroll events

UInputMapping = namedtuple("UInputMapping",
                           "name bustype vendor product version "
                           "axes axes_options buttons hats keys mouse "
                           "mouse_options")

_mappings = {}

# Add our simulated mousewheel codes
ecodes.REL_WHEELUP = 13      # Unique value for this lib
ecodes.REL_WHEELDOWN = 14    # Ditto


def parse_button(attr):
    if attr[0] in BUTTON_MODIFIERS:
        modifier = attr[0]
        attr = attr[1:]
    else:
        modifier = None

    return (attr, modifier)


def create_mapping(name, description, bustype=0, vendor=0, product=0,
                   version=0, axes={}, axes_options={}, buttons={},
                   hats={}, keys={}, mouse={}, mouse_options={}):
    axes = {getattr(ecodes, k): v for k,v in axes.items()}
    axes_options = {getattr(ecodes, k): v for k,v in axes_options.items()}
    buttons = {getattr(ecodes, k): parse_button(v) for k,v in buttons.items()}
    hats = {getattr(ecodes, k): v for k,v in hats.items()}
    mouse = {getattr(ecodes, k): parse_button(v) for k,v in mouse.items()}

    mapping = UInputMapping(description, bustype, vendor, product, version,
                            axes, axes_options, buttons, hats, keys, mouse,
                            mouse_options)
    _mappings[name] = mapping


# Pre-configued mappings
create_mapping(
    "ds4", "Sony Computer Entertainment Wireless Controller",
    # Bus type,     vendor, product, version
    ecodes.BUS_USB, 1356,   1476,    273,
    # Axes
    {
        "ABS_X":        "left_analog_x",
        "ABS_Y":        "left_analog_y",
        "ABS_Z":        "right_analog_x",
        "ABS_RZ":       "right_analog_y",
        "ABS_RX":       "l2_analog",
        "ABS_RY":       "r2_analog",
        "ABS_THROTTLE": "orientation_roll",
        "ABS_RUDDER":   "orientation_pitch",
        "ABS_WHEEL":    "orientation_yaw",
        "ABS_DISTANCE": "motion_z",
        "ABS_TILT_X":   "motion_x",
        "ABS_TILT_Y":   "motion_y",
    },
    # Axes options
    {
        "ABS_THROTTLE": (0, -16385, 16384, 0, 0),
        "ABS_RUDDER":   (0, -16385, 16384, 0, 0),
        "ABS_WHEEL":    (0, -16385, 16384, 0, 0),
        "ABS_DISTANCE": (0, -32768, 32767, 0, 10),
        "ABS_TILT_X":   (0, -32768, 32767, 0, 10),
        "ABS_TILT_Y":   (0, -32768, 32767, 0, 10),
    },
    # Buttons
    {
        "BTN_TR2":    "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_TL2":    "button_share",
        "BTN_B":      "button_cross",
        "BTN_C":      "button_circle",
        "BTN_A":      "button_square",
        "BTN_X":      "button_triangle",
        "BTN_Y":      "button_l1",
        "BTN_Z":      "button_r1",
        "BTN_TL":     "button_l2",
        "BTN_TR":     "button_r2",
        "BTN_SELECT": "button_l3",
        "BTN_START":  "button_r3",
        "BTN_THUMBL": "button_trackpad"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xboxdrv", "Xbox Gamepad (userspace driver)",
    # Bus type, vendor, product, version
    0,          0,      0,       0,
    # Axes
    {
        "ABS_X":     "left_analog_x",
        "ABS_Y":     "left_analog_y",
        "ABS_RX":    "right_analog_x",
        "ABS_RY":    "right_analog_y",
        "ABS_BRAKE": "l2_analog",
        "ABS_GAS":   "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xpad", "Microsoft X-Box 360 pad",
    # Bus type,      vendor, product, version
    ecodes.BUS_USB,  1118,   654,     272,
    # Axes
    {
        "ABS_X":  "left_analog_x",
        "ABS_Y":  "left_analog_y",
        "ABS_RX": "right_analog_x",
        "ABS_RY": "right_analog_y",
        "ABS_Z":  "l2_analog",
        "ABS_RZ": "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3"
    },
    # Hats
    {
        "ABS_HAT0X": ("dpad_left", "dpad_right"),
        "ABS_HAT0Y": ("dpad_up", "dpad_down")
    }
)

create_mapping(
    "xpad_wireless", "Xbox 360 Wireless Receiver",
    # Bus type,      vendor, product, version
    ecodes.BUS_USB,  1118,   1817,    256,
    # Axes
    {
        "ABS_X":  "left_analog_x",
        "ABS_Y":  "left_analog_y",
        "ABS_RX": "right_analog_x",
        "ABS_RY": "right_analog_y",
        "ABS_Z":  "l2_analog",
        "ABS_RZ": "r2_analog"
    },
    # Axes settings
    {},
    #Buttons
    {
        "BTN_START":  "button_options",
        "BTN_MODE":   "button_ps",
        "BTN_SELECT": "button_share",
        "BTN_A":      "button_cross",
        "BTN_B":      "button_circle",
        "BTN_X":      "button_square",
        "BTN_Y":      "button_triangle",
        "BTN_TL":     "button_l1",
        "BTN_TR":     "button_r1",
        "BTN_THUMBL": "button_l3",
        "BTN_THUMBR": "button_r3",

        "BTN_TRIGGER_HAPPY1": "dpad_left",
        "BTN_TRIGGER_HAPPY2": "dpad_right",
        "BTN_TRIGGER_HAPPY3": "dpad_up",
        "BTN_TRIGGER_HAPPY4": "dpad_down",
    },
)

create_mapping(
    "mouse", "DualShock4 Mouse Emulation",
    buttons={
        "BTN_LEFT": "button_trackpad",
    },
    mouse={
        "REL_X": "trackpad_touch0_x",
        "REL_Y": "trackpad_touch0_y"
    },
)


class UInputDevice(object):
    def __init__(self, layout):
        self.joystick_dev = None
        self.evdev_dev = None
        self.ignored_buttons = set()
        self.create_device(layout)

        self._write_cache = {}
        self._scroll_details = {}
        self.emit_reset()

    def create_device(self, layout):
        """Creates a uinput device using the specified layout."""
        events = {ecodes.EV_ABS: [], ecodes.EV_KEY: [],
                  ecodes.EV_REL: []}

        # Joystick device
        if layout.axes or layout.buttons or layout.hats:
            self.joystick_dev = next_joystick_device()

        for name in layout.axes:
            params = layout.axes_options.get(name, DEFAULT_AXIS_OPTIONS)
            if not absInfoUsesValue:
                params = params[1:]
            events[ecodes.EV_ABS].append((name, params))

        for name in layout.hats:
            params = (0, -1, 1, 0, 0)
            if not absInfoUsesValue:
                params = params[1:]
            events[ecodes.EV_ABS].append((name, params))

        for name in layout.buttons:
            events[ecodes.EV_KEY].append(name)

        if layout.mouse:
            self.mouse_pos = {}
            self.mouse_rel = {}
            self.mouse_analog_sensitivity = float(
                layout.mouse_options.get("MOUSE_SENSITIVITY",
                                         DEFAULT_MOUSE_SENSITIVTY)
            )
            self.mouse_analog_deadzone = int(
                layout.mouse_options.get("MOUSE_DEADZONE",
                                         DEFAULT_MOUSE_DEADZONE)
            )
            self.scroll_repeat_delay = float(
                layout.mouse_options.get("MOUSE_SCROLL_REPEAT_DELAY",
                                         DEFAULT_SCROLL_REPEAT_DELAY)
            )
            self.scroll_delay = float(
                layout.mouse_options.get("MOUSE_SCROLL_DELAY",
                                         DEFAULT_SCROLL_DELAY)
            )

            for name in layout.mouse:
                if name in (ecodes.REL_WHEELUP, ecodes.REL_WHEELDOWN):
                    if ecodes.REL_WHEEL not in events[ecodes.EV_REL]:
                        # This ensures that scroll wheel events can work
                        events[ecodes.EV_REL].append(ecodes.REL_WHEEL)
                else:
                    events[ecodes.EV_REL].append(name)
                self.mouse_rel[name] = 0.0

        self.device = UInput(name=layout.name, events=events,
                             bustype=layout.bustype, vendor=layout.vendor,
                             product=layout.product, version=layout.version)
        self.layout = layout

    def write_event(self, etype, code, value):
        """Writes a event to the device, if it has changed."""
        last_value = self._write_cache.get(code)
        if last_value != value:
            self.device.write(etype, code, value)
            self._write_cache[code] = value

    def emit(self, report):
        """Writes axes, buttons and hats with values from the report to
        the device."""
        for name, attr in self.layout.axes.items():
            value = getattr(report, attr)
            self.write_event(ecodes.EV_ABS, name, value)

        for name, attr in self.layout.buttons.items():
            attr, modifier = attr

            if attr in self.ignored_buttons:
                value = False
            else:
                value = getattr(report, attr)

            if modifier and "analog" in attr:
                if modifier == "+":
                    value = value > (128 + DEFAULT_A2D_DEADZONE)
                elif modifier == "-":
                    value = value < (128 - DEFAULT_A2D_DEADZONE)

            self.write_event(ecodes.EV_KEY, name, value)

        for name, attr in self.layout.hats.items():
            if getattr(report, attr[0]):
                value = -1
            elif getattr(report, attr[1]):
                value = 1
            else:
                value = 0

            self.write_event(ecodes.EV_ABS, name, value)

        self.device.syn()

    def emit_reset(self):
        """Resets the device to a blank state."""
        for name in self.layout.axes:
            params = self.layout.axes_options.get(name, DEFAULT_AXIS_OPTIONS)
            self.write_event(ecodes.EV_ABS, name, int(sum(params[1:3]) / 2))

        for name in self.layout.buttons:
            self.write_event(ecodes.EV_KEY, name, False)

        for name in self.layout.hats:
            self.write_event(ecodes.EV_ABS, name, 0)

        self.device.syn()

    def emit_mouse(self, report):
        """Calculates relative mouse values from a report and writes them."""
        for name, attr in self.layout.mouse.items():
            # If the attr is a tuple like (left_analog_y, "-")
            # then set the attr to just be the first item
            attr, modifier = attr

            if attr.startswith("trackpad_touch"):
                active_attr = attr[:16] + "active"
                if not getattr(report, active_attr):
                    self.mouse_pos.pop(name, None)
                    continue

                pos = getattr(report, attr)
                if name not in self.mouse_pos:
                    self.mouse_pos[name] = pos

                sensitivity = 0.5
                self.mouse_rel[name] += (pos - self.mouse_pos[name]) * sensitivity
                self.mouse_pos[name] = pos

            elif "analog" in attr:
                pos = getattr(report, attr)
                if (pos > (128 + self.mouse_analog_deadzone)
                    or pos < (128 - self.mouse_analog_deadzone)):
                    accel = (pos - 128) / 10
                else:
                    continue

                # If a minus modifier has been given then minus the acceleration
                # to invert the direction.
                if (modifier and modifier == "-"):
                    accel = -accel

                sensitivity = self.mouse_analog_sensitivity
                self.mouse_rel[name] += accel * sensitivity

            # Emulate mouse wheel (needs special handling)
            if name in (ecodes.REL_WHEELUP, ecodes.REL_WHEELDOWN):
                ecode = ecodes.REL_WHEEL # The real event we need to emit
                write = False
                if getattr(report, attr):
                    self._scroll_details['direction'] = name
                    now = time.time()
                    last_write = self._scroll_details.get('last_write')
                    if not last_write:
                        # No delay for the first button press for fast feedback
                        write = True
                        self._scroll_details['count'] = 0
                    if name == ecodes.REL_WHEELUP:
                        value = 1
                    elif name == ecodes.REL_WHEELDOWN:
                        value = -1
                    if last_write:
                        # Delay at least one cycle before continual scrolling
                        if self._scroll_details['count'] > 1:
                            if now - last_write > self.scroll_delay:
                                write = True
                        elif now - last_write > self.scroll_repeat_delay:
                            write = True
                    if write:
                        self.device.write(ecodes.EV_REL, ecode, value)
                        self._scroll_details['last_write'] = now
                        self._scroll_details['count'] += 1
                        continue # No need to proceed further
                else:
                    # Reset so you can quickly tap the button to scroll
                    if self._scroll_details.get('direction') == name:
                        self._scroll_details['last_write'] = 0
                        self._scroll_details['count'] = 0

            rel = int(self.mouse_rel[name])
            self.mouse_rel[name] = self.mouse_rel[name] - rel
            self.device.write(ecodes.EV_REL, name, rel)

        self.device.syn()


def create_uinput_device(mapping):
    """Creates a uinput device."""
    if mapping not in _mappings:
        raise DeviceError("Unknown device mapping: {0}".format(mapping))

    try:
        mapping = _mappings[mapping]
        device = UInputDevice(mapping)
    except UInputError as err:
        raise DeviceError(err)

    return device


def parse_uinput_mapping(name, mapping):
    """Parses a dict of mapping options."""
    axes, buttons, mouse, mouse_options = {}, {}, {}, {}
    description = "ds4drv custom mapping ({0})".format(name)

    for key, attr in mapping.items():
        key = key.upper()
        if key.startswith("BTN_") or key.startswith("KEY_"):
            buttons[key] = attr
        elif key.startswith("ABS_"):
            axes[key] = attr
        elif key.startswith("REL_"):
            mouse[key] = attr
        elif key.startswith("MOUSE_"):
            mouse_options[key] = attr

    create_mapping(name, description, axes=axes, buttons=buttons,
                   mouse=mouse, mouse_options=mouse_options)


def next_joystick_device():
    """Finds the next available js device name."""
    for i in range(100):
        dev = "/dev/input/js{0}".format(i)
        if not os.path.exists(dev):
            return dev
