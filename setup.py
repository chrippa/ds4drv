#!/usr/bin/env python

from setuptools import setup

setup(name="ds4drv",
      version="0.1.0",
      description="A DualShock 4 bluetooth driver for Linux",
      url="https://github.com/chrippa/ds4drv",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="MIT",
      entry_points={
          "console_scripts": ["ds4drv=ds4drv:main"]
      },
      py_modules=["ds4drv"],
      install_requires=["evdev"],
)

