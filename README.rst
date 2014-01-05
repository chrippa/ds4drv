======
ds4drv
======

ds4drv is a simple daemon that scans for DualShock 4 controllers via bluetooth,
connects to them and creates a joystick device. This driver does **NOT** work
via USB.


Background
----------

The Linux bluetooth driver bluez is currently not compatible with the
DS4 controller. ds4drv is just a quick hack to let me play games with this
awesome controller until it's supported properly in bluez. :-)


Features
--------

- Emulate the Xbox 360 controller for compatibility with Steam games
- Set the LED color
- Remind you about low battery by flashing the LED
- Use the trackpad as a mouse


Installing
----------

Make sure you have the dependencies:

- Python 2.7 or 3.3
- python-setuptools
- hcitool (usually available in the *bluez-utils* or equivalent package)


Then check out the source from Github and install it with:

.. code-block:: bash

    $ sudo python setup.py install


Using
-----

Simplest usage is to run it without any options:

.. code-block:: bash

   $ ds4drv

ds4drv does not support pairing, so to connect the controller you need to
start it in pairing mode every time you want to use it. This is done by holding
the Share and PS button until the LED starts blinking.

Permissions
^^^^^^^^^^^

ds4drv uses the kernel module uinput to create input devices in user land,
but this usually requires root permissions. You can change the permissions
by creating a udev rule. Put this in ``/etc/udev/rules.d/50-uinput.rules``:

.. code-block::

    KERNEL=="uinput", MODE="0666"


Configuring
-----------

You can also configure some options, this will set the LED to a bright red:

.. code-block:: bash

   $ ds4drv --led ff0000

See ``ds4drv --help`` for a list of all the options.


Multiple controllers
^^^^^^^^^^^^^^^^^^^^

ds4drv does in theory support multiple controllers (I only have one
controller myself, so this is untested). You can give each controller different
options like this:

.. code-block:: bash

   $ ds4drv --led ff0000 --next-controller --led 00ff00

This will set the LED color to red on the first controller connected and
green on the second.


Known issues/limitations
------------------------

- No pairing, you must start your controller in pairing mode everytime
- The controller will never be shut off, you need to do this manually by holding
  the PS button until the controller shuts off

References
----------

The DualShock 4 report format is not open and had to be reverse engineered.
These resources have been very helpful when creating ds4drv:

- http://www.psdevwiki.com/ps4/DualShock_4
- http://eleccelerator.com/wiki/index.php?title=DualShock_4
- https://gist.github.com/johndrinkwater/7708901
- https://github.com/ehd/node-ds4
- http://forums.pcsx2.net/Thread-DS4-To-XInput-Wrapper



