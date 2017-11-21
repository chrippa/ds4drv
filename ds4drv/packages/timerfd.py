"""
Copyright (c) 2010  Timo Savola <timo.savola@iki.fi>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = [
	"CLOEXEC",
	"NONBLOCK",

	"TIMER_ABSTIME",

	"CLOCK_REALTIME",
	"CLOCK_MONOTONIC",

	"bufsize",

	"timespec",
	"itimerspec",

	"create",
	"settime",
	"gettime",
	"unpack",
]

import ctypes
import ctypes.util
import math
import os
import struct

CLOEXEC         = 0o02000000
NONBLOCK        = 0o00004000

TIMER_ABSTIME   = 0x00000001

CLOCK_REALTIME  = 0
CLOCK_MONOTONIC = 1

bufsize         = 8

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

class timespec(ctypes.Structure):

	_fields_ = [
		("tv_sec",      libc.time.restype),
		("tv_nsec",     ctypes.c_long),
	]

	def __init__(self, time=None):
		ctypes.Structure.__init__(self)

		if time is not None:
			self.set_time(time)

	def __repr__(self):
		return "timerfd.timespec(%s)" % self.get_time()

	def set_time(self, time):
		fraction, integer = math.modf(time)

		self.tv_sec = int(integer)
		self.tv_nsec = int(fraction * 1000000000)

	def get_time(self):
		if self.tv_nsec:
			return self.tv_sec + self.tv_nsec / 1000000000.0
		else:
			return self.tv_sec

class itimerspec(ctypes.Structure):

	_fields_ = [
		("it_interval", timespec),
		("it_value",    timespec),
	]

	def __init__(self, interval=None, value=None):
		ctypes.Structure.__init__(self)

		if interval is not None:
			self.it_interval.set_time(interval)

		if value is not None:
			self.it_value.set_time(value)

	def __repr__(self):
		items = [("interval", self.it_interval), ("value", self.it_value)]
		args = ["%s=%s" % (name, value.get_time()) for name, value in items]
		return "timerfd.itimerspec(%s)" % ", ".join(args)

	def set_interval(self, time):
		self.it_interval.set_time(time)

	def get_interval(self):
		return self.it_interval.get_time()

	def set_value(self, time):
		self.it_value.set_time(time)

	def get_value(self):
		return self.it_value.get_time()

def errcheck(result, func, arguments):
	if result < 0:
		errno = ctypes.get_errno()
		raise OSError(errno, os.strerror(errno))

	return result

libc.timerfd_create.argtypes = [ctypes.c_int, ctypes.c_int]
libc.timerfd_create.errcheck = errcheck

libc.timerfd_settime.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(itimerspec), ctypes.POINTER(itimerspec)]
libc.timerfd_settime.errcheck = errcheck

libc.timerfd_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(itimerspec)]
libc.timerfd_gettime.errcheck = errcheck

def create(clock_id, flags=0):
	return libc.timerfd_create(clock_id, flags)

def settime(ufd, flags, new_value):
	old_value = itimerspec()
	libc.timerfd_settime(ufd, flags, ctypes.pointer(new_value), ctypes.pointer(old_value))
	return old_value

def gettime(ufd):
	curr_value = itimerspec()
	libc.timerfd_gettime(ufd, ctypes.pointer(curr_value))
	return curr_value

def unpack(buf):
	count, = struct.unpack("Q", buf[:bufsize])
	return count
