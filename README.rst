======
ds4drv
======

ds4drv is a Sony DualShock 4 userspace driver for Linux.

* Discussions: https://groups.google.com/forum/#!forum/ds4drv
* GitHub: https://github.com/chrippa/ds4drv
* PyPI: https://pypi.python.org/pypi/ds4drv

Features
--------

- Option to emulate the Xbox 360 controller for compatibility with Steam games
- Setting the LED color
- Reminding you about low battery by flashing the LED
- Using the trackpad as a mouse
- Custom mappings, map buttons and sticks to whatever mouse, key or joystick
  action you want
- Settings profiles that can be cycled through with a button binding


Installing
----------

Dependencies
^^^^^^^^^^^^

- `Python 2.7 or 3.3 <http://python.org/>`_ (for Debian/Ubuntu you need to
  install the *python2.7-dev* or *python3.3-dev* package)
- `python-setuptools <https://pythonhosted.org/setuptools/>`_
- hcitool (usually available in the *bluez-utils* or equivalent package)

These packages will normally be installed automatically by the setup script,
but you may want to use your distro's packages if available:

- `pyudev 0.16 or higher <http://pyudev.readthedocs.org/>`_
- `python-evdev 0.3.0 or higher <http://pythonhosted.org/evdev/>`_


Stable release
^^^^^^^^^^^^^^

Installing the latest release is simple by using `pip <http://www.pip-installer.org/>`_:

.. code-block:: bash

    $ sudo pip install ds4drv

Development version
^^^^^^^^^^^^^^^^^^^

If you want to try out latest development code check out the source from
Github and install it with:

.. code-block:: bash

    $ git clone https://github.com/chrippa/ds4drv.git
    $ cd ds4drv
    $ sudo python setup.py install


Using
-----

Raw bluetooth mode
^^^^^^^^^^^^^^^^^^

Prior to bluez 5.14 it was not possible to pair with the DS4. Therefore this
workaround exists which connects directly to the DS4 when it has been started
in pairing mode (by holding Share + PS until the LED starts blinking rapidly).

This is the default mode when running without any options:

.. code-block:: bash

   $ ds4drv


Hidraw mode
^^^^^^^^^^^

This mode supports connecting to already paired bluetooth devices (requires
bluez 5.14+) and devices connected by USB.

.. code-block:: bash

   $ ds4drv --hidraw

**Note:** Unfortunately due to a kernel bug it is currently not possible to use
any LED functionality when using bluetooth devices in this mode.


Permissions
^^^^^^^^^^^

ds4drv uses the kernel module *uinput* to create input devices in user land and
module *hidraw* to communicate with DualShock 4 controllers (when using
``--hidraw``), but this usually requires root permissions. You can change the
permissions by copying the `udev rules file <udev/50-ds4drv.rules>`_ to
``/etc/udev/rules.d/``.

You may have to reload your udev rules after this with:

.. code-block:: bash

    $ sudo udevadm control --reload-rules
    $ sudo udevadm trigger


Configuring
-----------

Configuration file
^^^^^^^^^^^^^^^^^^

The preferred way of configuring ds4drv is via a config file.
Take a look at `ds4drv.conf <ds4drv.conf>`_ for example usage.

ds4drv will look for the config file in the following paths:

- ``~/.config/ds4drv.conf``
- ``/etc/ds4drv.conf``

... or you can specify your own location with ``--config``.


Command line options
^^^^^^^^^^^^^^^^^^^^
You can also configure using command line options, this will set the LED
to a bright red:

.. code-block:: bash

   $ ds4drv --led ff0000

See ``ds4drv --help`` for a list of all the options.


Multiple controllers
^^^^^^^^^^^^^^^^^^^^

ds4drv does in theory support multiple controllers (I only have one
controller myself, so this is untested). You can give each controller
different options like this:

.. code-block:: bash

   $ ds4drv --led ff0000 --next-controller --led 00ff00

This will set the LED color to red on the first controller connected and
green on the second.


Known issues/limitations
------------------------

- The controller will never be shut off, you need to do this manually by
  holding the PS button until the controller shuts off
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

