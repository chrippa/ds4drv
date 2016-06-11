from ..action import Action
from ..audio import SBCHeaders


class AudioCallbacks():
    callbacks = []

    def __call__(self, buffer, data):
        import os
        #print("cbpid: ", os.getpid())
        for callback in self.callbacks:
            callback(data)

import os
from io import FileIO
hidraw_device = "/dev/hidraw3"
report_fd = os.open(hidraw_device, os.O_RDWR | os.O_NONBLOCK)
fd = FileIO(report_fd, "rb+", closefd=False)
class AudioAction(Action):
    """Plays audio through the device"""

    frame_number = 0
    audio_buffer = b''

    def setup(self, device):
        self.audio_pipeline = self.controller.audio_pipeline

        if not isinstance(self.audio_pipeline.get_callback(), AudioCallbacks):
            self.audio_pipeline.set_callback(AudioCallbacks())

        self.audio_pipeline.get_callback().callbacks.append(self.play_audio)

        self.audio_pipeline.restart()

    def play_audio(self, data):
        pos = 0
        sbc_headers = SBCHeaders()

        #print()
        #print("ld: ", len(data))
        import os
        #print("lpid:", os.getpid())
        while pos != len(data):
            sbc_headers.parse_header(data)
            frame_length = sbc_headers.calculate_frame_length()
            #print("fl: ", frame_length)

            self.controller.device.play_audio(sbc_headers,
                                              data[pos:pos + frame_length])
            #self.lplay_audio(None, data[pos:(pos+frame_length)])

            pos += frame_length
        #print("done")

    def lplay_audio(self, sbc_headers, data):
        print()
        print(len(self.audio_buffer))
        print(len(data))
        print()
        if len(self.audio_buffer) + len(data) <= 448:
            self.audio_buffer += data
            return
        print("running: ", len(self.audio_buffer))

        rumble_weak = 0
        rumble_strong = 0
        r = 0
        g = 0
        b = 10
        crc = b'\x00\x00\x00\x00'
        volume_speaker = 80
        volume_l = 60
        volume_r = 60
        unk2 = 100
        unk3 = 100
        flash_bright = 0
        flash_dark = 0
        #audio_header = b'\x24'
        audio_header = b'\x24'


        def frame_number(inc):
            import struct
            res = struct.pack("<H", self.frame_number)
            self.frame_number += inc
            if self.frame_number > 0xffff:
                self.frame_number = 0
            return res

        def joy_data():
            data = [0xff,0x4,0x00]
            #global volume_r,volume_unk2, unk3
            data.extend([rumble_weak,rumble_strong,r,g,b,flash_bright,flash_dark])
            data.extend([0]*8)
            data.extend([volume_l,volume_r,unk2,volume_speaker,unk3])
            return data


        def _11_report():
            data = joy_data()
            data.extend([0]*(48))
            return b'\x11\xC0\x20' + bytearray(data) + crc

        try:
            if self.reported_11 == True: pass
        except AttributeError:
            fd.write(_11_report())

        def _17_report(audo_data):
            return (
                b'\x17\x40\xA0'
                + frame_number(4)
                + audio_header
                + audo_data
                + bytearray(452 - len(audo_data)) + crc
            )
        report = _17_report(self.audio_buffer)

        print(data[0])
        self.audio_buffer = data

        #if self._volume_r == 0:
        #    self.set_volume(60, 60, 0)
        #    self._control()
        #self.write_report(report[0], report[1:])
        print(report)
        print(len(report))
        fd.write(report)
