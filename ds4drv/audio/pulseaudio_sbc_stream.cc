#include "pulseaudio_sbc_stream.hh"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdint.h>

#include <unistd.h>


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
    std::size_t sbc_frame_buflen = 10*sbc_frame_length+10;
    uint8_t sbc_frame_buf[sbc_frame_buflen];

    std::size_t sbc_audio_length = sbc_get_codesize(sbc);

    while(pa_stream_readable_size(s) > 0) {
        const char* data8 = NULL;
        std::size_t length = 0;

        pa_stream_peek(s, reinterpret_cast<const void**>(&data8), &length);

        self->audio_buffer.insert(
            self->audio_buffer.end(), data8, data8+length
        );

        if(self->audio_buffer.size() >= sbc_audio_length) {
            ssize_t written = 0;

            std::size_t read = sbc_encode(
                sbc,
                self->audio_buffer.linearize(), self->audio_buffer.size(),
                sbc_frame_buf, sbc_frame_buflen,
                &written
            );

            if(written > 0) {

                // Write frames to supplied file descriptors
                for(
                    FDList::iterator fd_it = self->fds.begin();
                    fd_it != self->fds.end();
                    fd_it++
                ) {
                    write(*fd_it, sbc_frame_buf, written);
                }

                self->audio_buffer.erase_begin(read);
            }
        }

        pa_stream_drop(s);
    }
}

void PulseaudioSBCStream::setup_pulse_stream(
    pa_context* c, const pa_sink_info* i, int eol, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    if(i && eol == 0 && i->owner_module == self->sink_module_id) {

        // Fix sbc encoder format

        // Endianness
        if(i->sample_spec.format == PA_SAMPLE_S16BE) {
            printf(
                "[info][PulseaudioSBCStream] "
                "Stream format s16be\n"
            );
            self->audio_loop_sbc.endian = SBC_BE;
        } else if(i->sample_spec.format == PA_SAMPLE_S16LE) {
            printf(
                "[info][PulseaudioSBCStream] "
                "Stream format s16le\n"
            );
            self->audio_loop_sbc.endian = SBC_LE;
        } else {
            printf(
                "[error][PulseaudioSBCStream] "
                "Unable to determine stream format\n"
            );
        }

        // Sample rate
        if(i->sample_spec.rate == 16000) {
            printf(
                "[info][PulseaudioSBCStream] "
                "Stream sample rate 16000\n"
            );
            self->audio_loop_sbc.frequency = SBC_FREQ_16000;
        } else if(i->sample_spec.rate == 32000) {
            printf(
                "[info][PulseaudioSBCStream] "
                "Stream sample rate 32000\n"
            );
            self->audio_loop_sbc.frequency = SBC_FREQ_32000;
        }

        // Some info
        std::size_t sbc_codesize = sbc_get_codesize(
            &(self->audio_loop_sbc)
        );
        std::size_t sbc_frame_length = sbc_get_frame_length(
            &(self->audio_loop_sbc)
        );
        printf(
            "[info][PulseaudioSBCStream] "
            "Stream codesize: %zu\n", sbc_codesize
        );
        printf(
            "[info][PulseaudioSBCStream] "
            "Stream frame_length: %zu\n", sbc_frame_length
        );


        // Set up stream
        pa_stream* stream = pa_stream_new(
            c, self->sink_description.c_str(), &(i->sample_spec), NULL
        );

        pa_stream_set_read_callback(stream, read_pulse_stream, self_v);


        pa_buffer_attr buffer_attr;
        buffer_attr.maxlength = (uint32_t) -1;
        buffer_attr.prebuf = (uint32_t) -1;
        buffer_attr.fragsize = (uint32_t) -1;
        buffer_attr.tlength = (uint32_t) -1;
        buffer_attr.minreq = (uint32_t) -1;
        buffer_attr.fragsize = pa_usec_to_bytes(4000, &(i->sample_spec));

        pa_stream_flags_t flags = static_cast<pa_stream_flags_t>(
            PA_STREAM_ADJUST_LATENCY
        );

        char device_strbuf[1024];
        snprintf(device_strbuf, 1024, "%s.monitor", i->name);
        pa_stream_connect_record(
            stream, device_strbuf, &buffer_attr, flags
        );
    }
}

void PulseaudioSBCStream::module_setup_cb(
    pa_context* c, uint32_t idx, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    self->sink_module_id = idx;

    pa_operation* op = pa_context_get_sink_info_list(
        c, setup_pulse_stream, self_v
    );
    if(op != NULL) pa_operation_unref(op);
}

void PulseaudioSBCStream::context_state_cb(pa_context* c, void* self_v) {
    Self* self = static_cast<Self*>(self_v);

    // Context connected. Setup stream.
    if(pa_context_get_state(c) == PA_CONTEXT_READY) {
        printf("[info][PulseaudioSBCStream] Connecting to Pulseaudio\n");

        Self* self = static_cast<Self*>(self_v);

        // Build new sink_description string with spaces escaped.
        std::string sanitized_description = self->sink_description;
        std::size_t last_pos = 0;
        std::size_t found = 0;
        while(
            (found = sanitized_description.find(' ', last_pos))
                != sanitized_description.npos
        ) {
            sanitized_description.replace(found, 1, "\\ ");
            last_pos = found + 2;
        }
        char options_buf[1024];
        snprintf(
            options_buf, 1024,
            "rate=\"%d\" format=\"%s\" channels=\"%d\""
            "sink_name=\"%s\" sink_properties=device.description=\"%s\"",
            self->sample_rate, pa_sample_format_to_string(PA_SAMPLE_S16NE), 2,
            self->sink_name.c_str(), sanitized_description.c_str()
        );
        pa_operation* op = pa_context_load_module(
            c, "module-null-sink", options_buf, module_setup_cb, self_v
        );
        if(op != NULL) pa_operation_unref(op);
    }

    // Context failed. Assume pulse will restart and try reconnecting.
    if(pa_context_get_state(c) == PA_CONTEXT_FAILED) {
        printf(
            "[info][PulseaudioSBCStream] Context failed. Reconnecting...\n"
        );

        unsigned int sleep_time = 1;

        // Try reconnecting every sleep_time seconds.
        while(self->setup_context() < 0) {
            sleep(sleep_time);
        }
    }
}

void PulseaudioSBCStream::unload_module_success(
    pa_context* c, int success, void* self_v
) {
    Self* self = static_cast<Self*>(self_v);

    pa_mainloop_api* api = pa_threaded_mainloop_get_api(self->mainloop);
    api->quit(api, 20);

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

    sample_rate(32000),

    audio_buffer(512*100)
{
    sbc_init(&(this->audio_loop_sbc), 0);

    this->audio_loop_sbc.frequency  = SBC_FREQ_32000; // Possibly reset later.
    this->audio_loop_sbc.blocks     = SBC_BLK_16;
    this->audio_loop_sbc.subbands   = SBC_SB_8;
    this->audio_loop_sbc.mode       = SBC_MODE_DUAL_CHANNEL;
    this->audio_loop_sbc.allocation = SBC_AM_LOUDNESS;
    this->audio_loop_sbc.bitpool    = 25;
    this->audio_loop_sbc.endian     = SBC_BE; // Possibly reset later.

    pa_threaded_mainloop* mainloop = pa_threaded_mainloop_new();
    this->mainloop = mainloop;

    this->setup_context();
}

PulseaudioSBCStream::~PulseaudioSBCStream() {
    this->stop();

    pa_context_disconnect(this->context);

    sbc_finish(&(this->audio_loop_sbc));
}

int PulseaudioSBCStream::setup_context() {
    pa_proplist* proplist = pa_proplist_new();
    pa_proplist_sets(
        proplist, PA_PROP_DEVICE_STRING, this->sink_name.c_str()
    );
    pa_proplist_sets(
        proplist, PA_PROP_DEVICE_DESCRIPTION, this->sink_description.c_str()
    );

    pa_context* c = pa_context_new_with_proplist(
        pa_threaded_mainloop_get_api(mainloop),
        this->sink_name.c_str(), proplist
    );

    this->context = c;

    int err = pa_context_connect(c, NULL, PA_CONTEXT_NOFLAGS, NULL);
    if(err >= 0) {
        pa_context_set_state_callback(c, context_state_cb, this);
    }
    else {
        printf("[error][PulseaudioSBCStream] Error connecting context\n");
    }

    return err;
}

void PulseaudioSBCStream::run() {
    int err = pa_threaded_mainloop_start(this->mainloop);
    if(err < 0) {
        printf("[error][PulseaudioSBCStream] Error starting mainloop\n");
    }
}

void PulseaudioSBCStream::stop() {
    printf("[info][PulseaudioSBCStream] Disconnecting from Pulseaudio\n");
    if(this->sink_module_id > 0) {
        pa_operation* op = pa_context_unload_module(
            this->context, this->sink_module_id,
            unload_module_success, this
        );
        if(op != NULL) pa_operation_unref(op);
    } else {
        unload_module_success(this->context, 0, this);
    }
}
