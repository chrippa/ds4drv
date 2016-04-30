
Release history
---------------

0.5.1 (2016-04-30)
^^^^^^^^^^^^^^^^^^

- Fixed compatibility with python-evdev 0.6.0 (#70)
- Fixed spurious input from unconnected devices (#59)


0.5.0 (2014-03-07)
^^^^^^^^^^^^^^^^^^

- Added a ``--ignored-buttons`` option.
- Added signal strength warnings to the log output.
- Changed deadzone to 5 (down from 15).
- Switched to event loop based report reading and timers.
- Mouse movement should now be smoother since it is now based on a timer
  instead of relying on reports arriving at a constant rate.
- Fixed issue where keys and buttons where not released on disconnect.
- Fixed crash when hcitool returns non-ascii data.


0.4.3 (2014-02-21)
^^^^^^^^^^^^^^^^^^

- A few performance improvements.
- Fixed prev-profile action.


0.4.2 (2014-02-15)
^^^^^^^^^^^^^^^^^^

- Fixed regressions in controller options handling causing issues
  with device creation and using joystick layouts in profiles.


0.4.1 (2014-02-14)
^^^^^^^^^^^^^^^^^^

- Daemon mode was accidentally left on by default in ds4drv.conf.


0.4.0 (2014-02-14)
^^^^^^^^^^^^^^^^^^

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


0.3.0 (2014-02-08)
^^^^^^^^^^^^^^^^^^

- Added hidraw mode, patch by Lauri Niskanen.
- Added config file support.
- Added custom button mapping.
- Added profiles.

- Fixed crash when using Python <2.7.4


0.2.1 (2014-01-26)
^^^^^^^^^^^^^^^^^^

- Updated ds4drv.service to read a config file, patch by George Gibbs.
- ``--led`` now accepts colors in the "#ffffff" format aswell.
- Added status updates in the log, patch by Lauri Niskanen.


0.2.0 (2014-01-24)
^^^^^^^^^^^^^^^^^^

- Added systemd service file, patch by George Gibbs.
- Added options: ``--emulate-xboxdrv`` and ``--emulate-xpad-wireless``.
- Fixed ``--emulate-xpad`` issues.


0.1.1 (2014-01-12)
^^^^^^^^^^^^^^^^^^

- Fixed incorrect dpad parsing.
- Handle uinput errors instead of printing exception.


0.1.0 (2014-01-07)
^^^^^^^^^^^^^^^^^^

- First release.


