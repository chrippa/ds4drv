from ..action import Action
from ..audio import SBCHeaders
from ..audio import pulseaudio_sbc_stream

import os

class AudioAction(Action):
    """Plays audio through the device"""

    def setup(self, device):
        self.sbc_stream = self.controller.sbc_stream
        self.loop = self.controller.loop

        self.read_pipe, self.write_pipe = os.pipe()

        self.sbc_stream.add_fd(self.write_pipe)

        self.loop.add_watcher(self.read_pipe, self.play_audio)


    def disable(self):
        self.sbc_stream.remove_fd(self.write_pipe)


    def play_audio(self):
        if not self.controller.device:
            return

        # Read the SBC header
        frame_header = os.read(self.read_pipe, 10)

        # Parse and find the length of the frame
        sbc_header = SBCHeaders()
        sbc_header.parse_header(frame_header)
        sbc_len = sbc_header.calculate_frame_length()

        # Read the rese of the frame
        rest_of_frame = os.read(self.read_pipe, sbc_len - 10)

        sbc_frame = frame_header + rest_of_frame

        # Call play_audio
        self.controller.device.play_audio(sbc_header, sbc_frame)
