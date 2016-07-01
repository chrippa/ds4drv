#!/usr/bin/env python

from . import pulseaudio_sbc_stream
from . import sbc_headers
from threading import Thread
import os
from select import epoll, EPOLLIN


class StreamReader(object):
    def __init__(self, sink_name, sink_description):
        self.sink_name = sink_name
        self.sink_description = sink_description

        self.continue_reading = True

        self.buffer_max = 10000
        self.buffer = pulseaudio_sbc_stream.CharArray(self.buffer_max)

        self.callbacks = []

        self.audio_stream = pulseaudio_sbc_stream.PulseaudioSBCStream(
            self.sink_name, self.sink_description
        )

        self.read_pipe, self.write_pipe = os.pipe()
        self.read_pipe_epoll = epoll()
        self.read_pipe_epoll.register(self.read_pipe, EPOLLIN)

        self.audio_stream.add_fd(self.write_pipe)

    def start(self):
        self.thread = Thread(target=self.run)
        self.thread.start()
        #print("running read_stream process done")

    def run(self):

        #print("Running audio_stream")
        self.audio_stream.run()

        while self.continue_reading == True:
            timeout = 1
            for fd, event in self.read_pipe_epoll.poll(timeout):
                # Read the SBC header
                frame_header = os.read(self.read_pipe, 10)

                # Parse and find the length of the frame
                sbc_header = sbc_headers.SBCHeaders()
                sbc_header.parse_header(frame_header)
                sbc_len = sbc_header.calculate_frame_length()

                # Read the rese of the frame
                rest_of_frame = os.read(self.read_pipe, sbc_len - 10)

                sbc_frame = frame_header + rest_of_frame

                for callback in self.callbacks:
                    callback(sbc_header, sbc_frame)

        self.audio_stream.stop()

    def stop(self):
        self.audio_stream.stop()
        self.continue_reading = False
        self.thread.join()

    def add_callback(self, callback):
        print("Adding callback", callback)
        self.callbacks.append(callback)
