from ..action import Action
from ..audio import SBCHeaders
from multiprocessing import RawArray, Manager
from ..audio import pulseaudio_sbc_stream

class AudioAction(Action):
    """Plays audio through the device"""

    def __init__(self, *args, **kwargs):
        super(AudioAction, self).__init__(*args, **kwargs)

    def setup(self, device):
        print("AudioAction Running setup")

        self.stream_reader = self.controller.stream_reader

        self.stream_reader.add_callback(
            self.play_audio
        )


    def disable(self):
        self.stream_reader.stop()


    def play_audio(self, sbc_header, sbc_frame):
        if not self.controller.device:
            return

        self.controller.device.play_audio(sbc_header, sbc_frame)

        return True
