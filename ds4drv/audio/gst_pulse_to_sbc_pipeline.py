import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, GstBase, GObject, Gtk

from multiprocessing import Process, Event
from threading import Thread, Event as tEvent
import subprocess

from .sbc_headers import SBCHeaders

Gst.init(None)
GObject.threads_init()

class CallbackSink(GstBase.BaseSink):
    __gstmetadata__ = (
        'CustomSink', 'Sink', 'custom test sink element', 'poconbhui'
    )
    __gsttemplates__ = Gst.PadTemplate.new(
        'sink',
        Gst.PadDirection.SINK,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.new_any()
    )

    def __init__(self, callback = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_callback(callback)

    def do_render(self, buffer):
        data = buffer.extract_dup(0, buffer.get_size())
        self.callback(buffer, data)
        return Gst.FlowReturn.OK
    
    def set_callback(self, callback):
        if callback == None:
            self.callback = lambda b, d: None
        else:
            self.callback = callback

    def get_callback(self):
        return self.callback


class ProcessWithWatcher(object):
    def __init__(self, target = None):
        self.target = target
        self.process = Process(target = target)
        self.end_watch = tEvent()

    def watch_target(self):
        while self.end_watch.is_set() != True:
            self.process.join()
            self.process = Process(target = self.target)
            self.process.start()

    def process(self):
        return self.process

    def start(self):
        self.process.start()
        self.start_watch()

    def join(self):
        self.stop_watch()
        self.process.join()

    def start_watch(self):
        self.watchman = Thread(target = self.watch_target)
        self.end_watch.clear()
        self.watchman.start()

    def stop_watch(self):
        self.end_watch.set()


class GstPulseToSBCPipeline(object):
    def __init__(self, pulse_sink_name='ds4'):
        self.pulse_sink_name = pulse_sink_name
        self.sink = CallbackSink()
        self.gtk_quit_main = Event()

    def run(self):
        import os
        print("fpsp:", os.getpid())

        self.player = Gst.Pipeline.new('player')


        self.pulse_source = Gst.ElementFactory.make(
            'pulsesrc', instance_name='pulse-source'
        )
        self.pulse_source.set_property(
            'device', self.pulse_sink_name + '.monitor'
        )

        self.player.add(self.pulse_source)


        self.pulse_buffer = Gst.ElementFactory.make(
            'queue', 'pulse-buffer'
        )

        self.player.add(self.pulse_buffer)
        self.pulse_source.link(self.pulse_buffer)


        self.pulse_resampler = Gst.ElementFactory.make(
            'audioresample', 'pulse-resampler'
        )

        self.player.add(self.pulse_resampler)
        self.pulse_buffer.link(self.pulse_resampler)


        self.pulse_resampler_caps = Gst.ElementFactory.make(
            'capsfilter', 'pulse-resampler-caps'
        )
        self.pulse_resampler_caps.set_property(
            'caps', Gst.Caps.from_string("audio/x-raw, rate=32000")
        )

        self.player.add(self.pulse_resampler_caps)
        self.pulse_resampler.link(self.pulse_resampler_caps)


        self.sbc_encoder = Gst.ElementFactory.make(
            'sbcenc', 'sbc-encoder'
        )

        self.player.add(self.sbc_encoder)
        self.pulse_resampler_caps.link(self.sbc_encoder)


        self.sbc_encoder_caps = Gst.ElementFactory.make(
            'capsfilter', 'sbc-encoder-caps'
        )
        self.sbc_encoder_caps.set_property(
            'caps', Gst.Caps.from_string(SBCHeaders().gst_sbc_caps())
        )

        self.player.add(self.sbc_encoder_caps)
        self.sbc_encoder.link(self.sbc_encoder_caps)


        self.sbc_encoder_buffer = Gst.ElementFactory.make(
            'queue', 'sbc-encoder-buffer'
        )

        self.player.add(self.sbc_encoder_buffer)
        self.sbc_encoder_caps.link(self.sbc_encoder_buffer)


        self.player.add(self.sink)
        self.sbc_encoder_buffer.link(self.sink)



        self.player.set_state(Gst.State.PLAYING)


        print("here: ", self.gtk_quit_main.is_set())
        while self.gtk_quit_main.is_set() != True:
            Gtk.main_iteration_do(False)
        print("Ran gtk main")


    def start(self):
        # Create pulse source
        pulse_sink_id = subprocess.check_output([
                'pactl', 'load-module', 'module-null-sink',
                'sink_name="{}"'.format(self.pulse_sink_name),
                'sink_properties=device.description="{}"'.format(                    
                        "DualShock\ 4"
                ), 
        ])
        self.pulse_sink_id = int(pulse_sink_id)
        print("pulse sink id:", pulse_sink_id)

        import os
        print("sis:", os.getpid())
        self.gst_process = ProcessWithWatcher(target = self.run)
        self.gst_process.start()
        print("sgsp:", self.gst_process)


    def stop(self):

        import os
        print("qid:", os.getpid())
        print("qgsp:", self.gst_process)
        self.gtk_quit_main.set()
        print("qran")
        self.gst_process.join()
        print("qgst_joined")

        subprocess.check_output([
                'pactl', 'unload-module', str(self.pulse_sink_id)
        ])

    def restart(self):
        print("starting restart")
        self.gtk_quit_main.set()
        print("a: ", self.gtk_quit_main.is_set())
        self.gst_process.join()
        self.gst_process = ProcessWithWatcher(target = self.run)
        self.gtk_quit_main.clear()
        print("b: ", self.gtk_quit_main.is_set())
        self.gst_process.start()
        print("restarted")
    
    def set_callback(self, callback):
        self.sink.set_callback(callback)

    def get_callback(self):
        return self.sink.get_callback()
