#!/usr/bin/env python

from setuptools import setup, Extension
import subprocess

from setuptools.command.build_ext import build_ext as _build_ext, log
from distutils import dir_util
import os.path
class build_ext(_build_ext):
    def swig_sources(self, sources, extension):
        """Patch swig_sources so wrap files are put in build_tmp and
        generated .py files are put in build."""
        new_sources = []
        swig_sources = []
        swig_targets = {}

        for source in sources:
            (base, ext) = os.path.splitext(source)
            if ext == ".i":             # SWIG interface file
                new_sources.append(
                    os.path.join(self.build_temp, base + '_wrap.cpp')
                )
                swig_sources.append(source)
                swig_targets[source] = new_sources[-1]
            else:
                new_sources.append(source)

        if not swig_sources:
            return new_sources

        swig = self.swig or self.find_swig()
        swig_cmd = [swig, "-python"]
        swig_cmd.extend(self.swig_opts)
        if self.swig_cpp:
            swig_cmd.append("-c++")

        # Do not override commandline arguments
        if not self.swig_opts:
            for o in extension.swig_opts:
                swig_cmd.append(o)

        for source in swig_sources:
            target = swig_targets[source]
            outdir = os.path.join(self.build_lib, os.path.dirname(source))

            dir_util.mkpath(os.path.dirname(target))
            dir_util.mkpath(outdir)

            log.info("swigging %s to %s", source, target)
            self.spawn(swig_cmd + ["-outdir", outdir, "-o", target, source])

        return new_sources


readme = open("README.rst").read()
history = open("HISTORY.rst").read()

setup(name="ds4drv",
      version="0.5.1",
      description="A Sony DualShock 4 userspace driver for Linux",
      url="https://github.com/chrippa/ds4drv",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="MIT",
      long_description=readme + "\n\n" + history,
      entry_points={
        "console_scripts": ["ds4drv=ds4drv.__main__:main"]
      },
      packages=["ds4drv",
                "ds4drv.actions",
                "ds4drv.backends",
                "ds4drv.packages",
                "ds4drv.audio"],
      cmdclass={'build_ext': build_ext},
      ext_modules=[
        Extension(
          "ds4drv.audio._pulseaudio_sbc_stream",
          [
            "ds4drv/audio/pulseaudio_sbc_stream.cc",
            "ds4drv/audio/pulseaudio_sbc_stream.i"
          ],
          swig_opts=["-c++", "-Ids4drv"],
          include_dirs=["ds4drv"],
          extra_compile_args=[
            subprocess.check_output(
                "pkg-config --cflags libpulse", shell=True
            ).decode('utf-8'),
            '-std=c++98'
          ],
          libraries=["pulse", "sbc"]
        )
      ],
      py_modules=['ds4drv.audio.pulseaudio_sbc_stream'],
      install_requires=["evdev>=0.3.0", "pyudev>=0.16"],
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

