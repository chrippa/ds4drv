import os.path

from collections import namedtuple

from evdev import UInput, UInputError, ecodes

from .exceptions import DeviceError

A2D_DEADZONE = 50

UInputMapping = namedtuple("UInputMapping",
                           "name bustype vendor product version "
                           "axes axes_options buttons hats keys mouse "
                           "mouse_options")

_mappings = {}


def create_mapping(name, description, bustype=0, vendor=0, product=0,
                   version=0, axes={}, axes_options={}, buttons={},
                   hats={}, keys={}, mouse={}, mouse_options={}):
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
        "ABS_THROTTLE": (-16385, 16384, 0, 0),
        "ABS_RUDDER":   (-16385, 16384, 0, 0),
        "ABS_WHEEL":    (-16385, 16384, 0, 0),
        "ABS_DISTANCE": (-32768, 32767, 0, 10),
        "ABS_TILT_X":   (-32768, 32767, 0, 10),
        "ABS_TILT_Y":   (-32768, 32767, 0, 10),
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

    def create_device(self, layout):
        events = {ecodes.EV_ABS: [], ecodes.EV_KEY: [],
                  ecodes.EV_REL: []}

        # Joystick device
        if layout.axes or layout.buttons or layout.hats:
            self.joystick_dev = next_joystick_device()

        for name in layout.axes:
            key = getattr(ecodes, name)
            params = layout.axes_options.get(name, (0, 255, 0, 15))
            events[ecodes.EV_ABS].append((key, params))

        for name in layout.hats:
            key = getattr(ecodes, name)
            params = (-1, 1, 0, 0)
            events[ecodes.EV_ABS].append((key, params))

        for name in layout.buttons:
            events[ecodes.EV_KEY].append(getattr(ecodes, name))

        if layout.mouse:
            self.mouse_pos = {}
            self.mouse_rel = {}
            self.mouse_analog_sensitivity = float(layout.mouse_options.get("MOUSE_SENSITIVITY", 0.3))
            self.mouse_analog_deadzone = int(layout.mouse_options.get("MOUSE_DEADZONE", 5))

            for name in layout.mouse:
                events[ecodes.EV_REL].append(getattr(ecodes, name))
                self.mouse_rel[name] = 0.0

        self.device = UInput(name=layout.name, events=events,
                             bustype=layout.bustype, vendor=layout.vendor,
                             product=layout.product, version=layout.version)
        self.layout = layout

    def emit(self, report):
        for name, attr in self.layout.axes.items():
            name = getattr(ecodes, name)
            value = getattr(report, attr)
            self.device.write(ecodes.EV_ABS, name, value)

        for name, attr in self.layout.buttons.items():
            name = getattr(ecodes, name)

            if attr[0] in ("+", "-"):
                modifier = attr[0]
                attr = attr[1:]
            else:
                modifier = False

            if attr in self.ignored_buttons:
                value = False
            else:
                value = getattr(report, attr)

            if modifier and "analog" in attr:
                if modifier == "+":
                    value = value > (128 + A2D_DEADZONE)
                elif modifier == "-":
                    value = value < (128 - A2D_DEADZONE)

            self.device.write(ecodes.EV_KEY, name, value)

        for name, attr in self.layout.hats.items():
            name = getattr(ecodes, name)
            if getattr(report, attr[0]):
                value = -1
            elif getattr(report, attr[1]):
                value = 1
            else:
                value = 0

            self.device.write(ecodes.EV_ABS, name, value)

        if self.layout.mouse:
            self.emit_mouse(report)

        self.device.syn()

    def emit_mouse(self, report):
        for name, attr in self.layout.mouse.items():
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

                sensitivity = self.mouse_analog_sensitivity
                self.mouse_rel[name] += accel * sensitivity

            rel = int(self.mouse_rel[name])
            self.mouse_rel[name] = self.mouse_rel[name] - rel
            self.device.write(ecodes.EV_REL, getattr(ecodes, name), rel)



def create_uinput_device(mapping):
    if mapping not in _mappings:
        raise DeviceError("Unknown device mapping: {0}".format(mapping))

    try:
        mapping = _mappings[mapping]
        device = UInputDevice(mapping)
    except UInputError as err:
        raise DeviceError(err)

    return device


def parse_uinput_mapping(name, mapping):
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
    for i in range(100):
        dev = "/dev/input/js{0}".format(i)
        if not os.path.exists(dev):
            return dev

