======
ds4drv
======

ds4drv is a simple daemon that scans for DualShock 4 controllers via bluetooth,
connects to them and creates a joystick device. This driver does **NOT** work
via USB.


Background
----------

When I first got my DS4 controller I expected it work without any issues
with Linux as it had been reported all over the internet that DS4 was a
standard HID device and required no special drivers. This turned out not
to be the case though, as when I attempted a standard pairing in Linux via
bluetoothctl I only ended up with strange error messages.

I tried asking for help on the
`bluez mailing list <http://comments.gmane.org/gmane.linux.bluez.kernel/42097>`_
but received no response. I tried to Google to find out if anyone else
had succeed to use the DS4 via bluetooth, but found no success stories.
I even tried to dig into the bluez code, but the error messages are very
strange and doesn't seem to describe what is going wrong at all, so I
didn't get anywhere there either.

So I tried experimenting with connecting directly to the HID channels,
just like the `libcwiid library <http://abstrakraft.org/cwiid/>`_ do with
the Wiimote, and, it worked! Since I now had access to the raw HID report,
I figured I might as well write a small driver to convert them into joystick
events, and here it is, ds4drv!

**Update (2014-01-21):** `Bluez 5.14 <http://www.bluez.org/bluez-5-14/>`_ has been
released which contains support for the DS4. This project is therefore only useful
if you want to access any features not yet supported by the Linux kernel, such as LED
color or trackpad mouse.


Features
--------

- Option to emulate the Xbox 360 controller for compatibility with Steam games
- Setting the LED color
- Reminding you about low battery by flashing the LED
- Using the trackpad as a mouse


Installing
----------

Make sure you have the dependencies:

- Python 2.7 or 3.3 (for Debian/Ubuntu you need to install the *python2.7-dev* or the *python3.3-dev* package)
- python-setuptools
- hcitool (usually available in the *bluez-utils* or equivalent package)

Installing the latest release via `pip <http://www.pip-installer.org/>`_:

.. code-block:: bash

    $ sudo pip install ds4drv

or if you want to run the latest development code, check out the source
from Github and install it with:

.. code-block:: bash

    $ sudo python setup.py install


Using
-----

Simplest usage is to run it without any options:

.. code-block:: bash

   $ ds4drv

**Note:** ds4drv does not support pairing, so to connect the controller you need to
start it in pairing mode every time you want to use it. This is done by holding
the Share and PS button until the LED starts blinking.

Permissions
^^^^^^^^^^^

ds4drv uses the kernel module uinput to create input devices in user land,
but this usually requires root permissions. You can change the permissions
by creating a udev rule. Put this in ``/etc/udev/rules.d/50-uinput.rules``:

::

    KERNEL=="uinput", MODE="0666"

You may have to reload your udev rules after this with:

.. code-block:: bash

    $ sudo udevadm control --reload-rules
    $ sudo udevadm trigger


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
- No rumble support

References
----------

The DualShock 4 report format is not open and had to be reverse engineered.
These resources have been very helpful when creating ds4drv:

- http://www.psdevwiki.com/ps4/DualShock_4
- http://eleccelerator.com/wiki/index.php?title=DualShock_4
- https://gist.github.com/johndrinkwater/7708901
- https://github.com/ehd/node-ds4
- http://forums.pcsx2.net/Thread-DS4-To-XInput-Wrapper



