import os.path

from collections import namedtuple

from evdev import UInput, UInputError, ecodes

from .exceptions import JoystickError

JoystickLayout = namedtuple("JoystickLayout",
                            "name bustype vendor product version "
                            "axes axes_options buttons hats")


JOYSTICK_LAYOUTS = {
    "ds4": JoystickLayout(
        "Sony Computer Entertainment Wireless Controller",
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
    ),

    "xboxdrv": JoystickLayout(
        "Xbox Gamepad (userspace driver)",
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
    ),

    "xpad": JoystickLayout(
        "Microsoft X-Box 360 pad",
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
    ),

    "xpad_wireless": JoystickLayout(
        "Xbox 360 Wireless Receiver",
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
        # Hats
        {}
    )
}

def next_joystick_device():
    for i in range(100):
        dev = "/dev/input/js{0}".format(i)
        if not os.path.exists(dev):
            return dev


class UInputDevice(object):
    def __init__(self, layout, mouse=False):
        self.mouse = None
        self.jsdev = next_joystick_device()
        self.create_joystick(layout)

        if mouse:
            self.create_mouse()

    def create_mouse(self):
        events = {
            ecodes.EV_REL: (ecodes.REL_X, ecodes.REL_Y),
            ecodes.EV_KEY: (ecodes.BTN_LEFT, ecodes.BTN_RIGHT)
        }
        self.mouse = UInput(events)
        self.mouse_pos = None

    def create_joystick(self, layout):
        events = {ecodes.EV_ABS: [], ecodes.EV_KEY: []}

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

        self.joystick = UInput(name=layout.name, events=events,
                               bustype=layout.bustype, vendor=layout.vendor,
                               product=layout.product, version=layout.version)
        self.layout = layout

    def emit(self, report):
        self.emit_joystick(report)

        if self.mouse:
            self.emit_mouse(report)

    def emit_joystick(self, report):
        for name, attr in self.layout.axes.items():
            name = getattr(ecodes, name)
            value = getattr(report, attr)

            self.joystick.write(ecodes.EV_ABS, name, value)

        for name, attr in self.layout.buttons.items():
            name = getattr(ecodes, name)
            value = getattr(report, attr)
            self.joystick.write(ecodes.EV_KEY, name, value)

        for name, attr in self.layout.hats.items():
            name = getattr(ecodes, name)
            if getattr(report, attr[0]):
                value = -1
            elif getattr(report, attr[1]):
                value = 1
            else:
                value = 0

            self.joystick.write(ecodes.EV_ABS, name, value)

        self.joystick.syn()

    def emit_mouse(self, report):
        if report.trackpad_touch0_active:
            if not self.mouse_pos:
                self.mouse_pos = (report.trackpad_touch0_x,
                                  report.trackpad_touch0_y)

            sensitivity = 0.5
            rel_x = (report.trackpad_touch0_x - self.mouse_pos[0]) * sensitivity
            rel_y = (report.trackpad_touch0_y - self.mouse_pos[1]) * sensitivity

            self.mouse.write(ecodes.EV_REL, ecodes.REL_X, int(rel_x))
            self.mouse.write(ecodes.EV_REL, ecodes.REL_Y, int(rel_y))
            self.mouse_pos = (report.trackpad_touch0_x, report.trackpad_touch0_y)
        else:
            self.mouse_pos = None

        self.mouse.write(ecodes.EV_KEY, ecodes.BTN_LEFT,
                         int(report.button_trackpad))
        self.mouse.syn()


def create_joystick(layout, mouse=False):
    layout = JOYSTICK_LAYOUTS.get(layout)

    if not layout:
        raise JoystickError("Unknown joystick layout: {0}", layout)

    try:
        joystick = UInputDevice(layout, mouse=mouse)
    except UInputError as err:
        raise JoystickError(err)

    return joystick
