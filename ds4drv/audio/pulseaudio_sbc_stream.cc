#include "pulseaudio_sbc_stream.hh"

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <unistd.h>
//#include <signal.h>


#include <pulse/pulseaudio.h>


void PulseaudioSBCStream::add_fd(int fd) {
    this->fds.insert(fd);
}

void PulseaudioSBCStream::remove_fd(int fd) {
    this->fds.erase(fd);
}

void PulseaudioSBCStream::read_pulse_stream(
    pa_stream *s, std::size_t length, void *self_v
) {
    Self* self = static_cast<Self*>(self_v);

    sbc_t* sbc = &(self->audio_loop_sbc);

    std::size_t sbc_frame_length = sbc_get_frame_length(sbc);
    std::size_t sbc_buflen = 10*sbc_frame_length+10;
    std::uint8_t sbc_buf[sbc_buflen];

    while(pa_stream_readable_size(s) > 0) {
        const char* data8 = NULL;
        std::size_t length = 0;

        pa_stream_peek(s, reinterpret_cast<const void**>(&data8), &length);

        self->audio_buffer.insert(
            self->audio_buffer.end(), data8, data8+length
        );

        for(std::size_t i=0; i<sbc_buflen; i++) {
            sbc_buf[i] = 0;
        }

        ssize_t written = 0;
        std::size_t read = sbc_encode(
            sbc,
            &(self->audio_buffer[0]), self->audio_buffer.size(),
            sbc_buf, sbc_buflen,
            &written
        );

        if(written > 0) {
            // Write frames to supplied file descriptors
            for(
                FDList::iterator fd_it = self->fds.begin();
                fd_it != self->fds.end();
                fd_it++
            ) {
                write(*fd_it, sbc_buf, written);
            }

            self->audio_buffer.erase(
                self->audio_buffer.begin(), self->audio_buffer.begin() + read
            );
        }

        pa_stream_drop(s);
    }
}

void PulseaudioSBCStream::setup_pulse_stream(
    pa_context* c, const pa_sink_info* i, int eol, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    if(i && eol == 0 && i->owner_module == self->sink_module_id) {

        pa_proplist* sink_proplist = i->proplist;
        int err = pa_proplist_sets(
            sink_proplist, PA_PROP_DEVICE_DESCRIPTION, "TEST AUDIO SINK"
        );

        /* Set up stream */
        char samplebuf[1024];
        pa_sample_spec_snprint(samplebuf, 1024, &(i->sample_spec));

        pa_stream* stream = pa_stream_new(
            c, "" /*"STR_DS4TEST"*/, &(i->sample_spec), NULL
        );

        pa_stream_set_read_callback(stream, read_pulse_stream, self_v);


        pa_buffer_attr buffer_attr;
        buffer_attr.maxlength = (uint32_t) -1;
        buffer_attr.prebuf = (uint32_t) -1;
        buffer_attr.fragsize = (uint32_t) -1;
        buffer_attr.tlength = (uint32_t) -1;
        buffer_attr.minreq = (uint32_t) -1;
        buffer_attr.fragsize = pa_usec_to_bytes(50, &(i->sample_spec));

        pa_stream_flags_t flags = PA_STREAM_ADJUST_LATENCY;

        char device_strbuf[1024];
        snprintf(device_strbuf, 1024, "%s.monitor", i->name);
        int screrr = pa_stream_connect_record(
            stream, device_strbuf, &buffer_attr, flags
        );
    }
}

void PulseaudioSBCStream::module_setup_cb(
    pa_context* c, uint32_t idx, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    self->sink_module_id = idx;

    pa_context_get_sink_info_list(
        c, setup_pulse_stream, self_v
    );
}

void PulseaudioSBCStream::context_state_cb(pa_context* c, void* self_v) {
    if(pa_context_get_state(c) == PA_CONTEXT_CONNECTING) {
        signal(SIGINT, SIG_IGN);
    }

    if(pa_context_get_state(c) == PA_CONTEXT_READY) {
        printf("[info][PulseaudioSBCStream] Connecting to Pulseaudio\n");

        Self* self = static_cast<Self*>(self_v);

        char options_buf[1024];
        snprintf(
            options_buf, 1024,
            "sink_name=\"%s\" rate=\"%d\" "
            "sink_properties=device.description=\"%s\"",
            self->sink_name.c_str(), 32000, self->sink_description.c_str()
        );
        pa_context_load_module(
            c, "module-null-sink", options_buf, module_setup_cb, self_v
        );
        
    }
}

void PulseaudioSBCStream::unload_module_success(
    pa_context* c, int success, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    pa_threaded_mainloop_get_api(self->mainloop)->quit(
        pa_threaded_mainloop_get_api(self->mainloop), 20
    );

    printf("[info][PulseaudioSBCStream] Disconnect successful\n");
}

PulseaudioSBCStream::PulseaudioSBCStream(
    std::string sink_name,
    std::string sink_description
):
    context(NULL),
    sink_name(sink_name),
    sink_description(sink_description),
    sink_module_id(-1),

    audio_buffer()
{
    sbc_init(&(this->audio_loop_sbc), 0);

    this->audio_loop_sbc.frequency  = SBC_FREQ_32000;
    this->audio_loop_sbc.blocks     = SBC_BLK_16;
    this->audio_loop_sbc.subbands   = SBC_SB_8;
    this->audio_loop_sbc.mode       = SBC_MODE_STEREO;
    this->audio_loop_sbc.allocation = SBC_AM_LOUDNESS;
    this->audio_loop_sbc.bitpool    = 50;
    this->audio_loop_sbc.endian     = SBC_LE;

    pa_threaded_mainloop* mainloop = pa_threaded_mainloop_new();
    this->mainloop = mainloop;

    pa_proplist* proplist = pa_proplist_new();
    pa_proplist_sets(
        proplist, PA_PROP_DEVICE_STRING, this->sink_name.c_str()
    );
    pa_proplist_sets(
        proplist, PA_PROP_DEVICE_DESCRIPTION, this->sink_description.c_str()
    );

    pa_context* c = pa_context_new_with_proplist(
        pa_threaded_mainloop_get_api(mainloop), "DS4TEST", proplist
    );

    this->context = c;

    int err = pa_context_connect(c, NULL, PA_CONTEXT_NOFLAGS, NULL);
    pa_context_set_state_callback(c, context_state_cb, this);
}

PulseaudioSBCStream::~PulseaudioSBCStream() {
    pa_context_disconnect(this->context);

    sbc_finish(&(this->audio_loop_sbc));
}

void PulseaudioSBCStream::run() {
    int err = pa_threaded_mainloop_start(this->mainloop);
}

void PulseaudioSBCStream::stop() {
    printf("[info][PulseaudioSBCStream] Disconnecting from Pulseaudio\n");
    if(this->sink_module_id > 0) {
        pa_context_unload_module(
            this->context, this->sink_module_id,
            unload_module_success, this
        );
    } else {
        unload_module_success(this->context, 0, this);
    }
}
