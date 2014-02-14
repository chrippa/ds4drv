
Release history
---------------

0.4.0
^^^^^

- Added ``--dump-reports`` option, patch by Lauri Niskanen.
- Added support for binding buttons combos to special actions.
- Fixed crash when multiple controllers where used.
- Fixed python-evdev version requirement.
- Fixed pyudev version requirement.
- Fixed duplicate devices when connecting a USB cable to a already
  connected Bluetooth device in hidraw mode.
- Improved mouse movement and configuration, patch by Lauri Niskanen.
- Changed button combo behaviour slightly. Now triggers when the
  last button of a combo is released instead of waiting for the
  whole combo to be released.


0.3.0
^^^^^

- Added hidraw mode, patch by Lauri Niskanen.
- Added config file support.
- Added custom button mapping.
- Added profiles.

- Fixed crash when using Python <2.7.4


0.2.1
^^^^^

- Updated ds4drv.service to read a config file, patch by George Gibbs.
- ``--led`` now accepts colors in the "#ffffff" format aswell.
- Added status updates in the log, patch by Lauri Niskanen.


0.2.0
^^^^^

- Added systemd service file, patch by George Gibbs.
- Added options: ``--emulate-xboxdrv`` and ``--emulate-xpad-wireless``.
- Fixed ``--emulate-xpad`` issues.


0.1.1
^^^^^

- Fixed incorrect dpad parsing.
- Handle uinput errors instead of printing exception.


0.1.0
^^^^^

- First release.


