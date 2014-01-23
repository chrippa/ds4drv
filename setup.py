#!/usr/bin/env python

from setuptools import setup

readme = open("README.rst").read()
history = open("HISTORY.rst").read()

setup(name="ds4drv",
      version="0.2.0",
      description="A DualShock 4 bluetooth driver for Linux",
      url="https://github.com/chrippa/ds4drv",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="MIT",
      long_description=readme + "\n\n" + history,
      entry_points={
        "console_scripts": ["ds4drv=ds4drv:main"]
      },
      py_modules=["ds4drv"],
      install_requires=["evdev"],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Topic :: Games/Entertainment"
      ]
)

