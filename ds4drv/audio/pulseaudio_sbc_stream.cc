#include "pulseaudio_sbc_stream.hh"

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <unistd.h>
//#include <signal.h>


#include <pulse/pulseaudio.h>



#define eprintf(...) fprintf(stderr, __VA_ARGS__)


void PulseaudioSBCStream::add_fd(int fd) {
    eprintf("PulseaudioSBCStream::add_fd %d\n", fd);
    this->fds.insert(fd);
    eprintf("Num fds: %zu\n", this->fds.size());
}

void PulseaudioSBCStream::remove_fd(int fd) {
    eprintf("PulseaudioSBCStream::remove_fd %d\n", fd);
    this->fds.erase(fd);
    eprintf("Num fds: %zu\n", this->fds.size());
}

void PulseaudioSBCStream::stream_read_cb(
    pa_stream *s, std::size_t length, void *self_v
) {
    Self* self = static_cast<Self*>(self_v);

    //printf("Stream write callback: Ready to write %zu bytes\n", length);

    sbc_t* sbc = &(self->audio_loop_sbc);
    std::size_t sbc_frame_length = sbc_get_frame_length(sbc);
    std::size_t sbc_buflen = 10*sbc_frame_length+10;
    std::uint8_t sbc_buf[sbc_buflen];
    //eprintf("sb start\n");
    while(pa_stream_readable_size(s) > 0) {
        //const void* data = NULL;
        const char* data8 = NULL;
        //char* audio_buffer8 = self->audio_buffer;
        std::size_t length = 0;

        pa_stream_peek(s, reinterpret_cast<const void**>(&data8), &length);
        //eprintf("datalen: %zu\n", length);

        self->audio_buffer.insert(
            self->audio_buffer.end(), data8, data8+length
        );

        //eprintf("audio_buffer_pos: %zu\n", self->audio_buffer_pos);

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
                //eprintf("PulseaudioSBCStream:: Writing to fd\n");
                //eprintf("Written: %zu\n", written);
                //eprintf("Syncword: %d\n", sbc_buf[0]);
                write(*fd_it, sbc_buf, written);
            }

            self->audio_buffer.erase(
                self->audio_buffer.begin(), self->audio_buffer.begin() + read
            );
        }

        pa_stream_drop(s);
    }
    //eprintf("sb end\n");
  
}

void PulseaudioSBCStream::stream_state_cb(pa_stream *s, void *self_v) {

    //printf("stream state\n");
    pa_stream_state_t sst = pa_stream_get_state(s);
    switch(sst) {
    case PA_STREAM_UNCONNECTED:
        //printf("psu\n");
        break;
    case PA_STREAM_CREATING:
        //printf("psc\n");
        break;
    case PA_STREAM_TERMINATED:
        //printf("pst\n");
        break;
    case PA_STREAM_READY:
        //printf("psr\n");
        break;
    case PA_STREAM_FAILED:
        //printf("psf\n");
        //printf("Stream error: %s\n", pa_strerror(pa_context_errno(pa_stream_get_context(s))));

        break;
    }

    if(pa_stream_get_state(s) == PA_STREAM_READY) {
        //printf("Stream Ready\n");
    }
}


void PulseaudioSBCStream::stream_success_cb(
    pa_stream *s, int success, void* self_v
) {
    //printf("Stream success cb %d\n", success);

    // TODO: Read stream, SBCenc and to ds4 callback
}

void PulseaudioSBCStream::stream_overflow_cb(pa_stream* p, void* self_v) {
    eprintf("Buffer overflow\n");
}

void PulseaudioSBCStream::stream_underflow_cb(pa_stream* p, void* self_v) {
    eprintf("Buffer underflow\n");
}

void PulseaudioSBCStream::sink_info_cb(
    pa_context* c, const pa_sink_info* i, int eol, void* self_v
) {
    eprintf("sib %p %d\n", i, eol);
    Self* self = static_cast<Self*>(self_v);

    if(i && eol == 0 && i->owner_module == self->sink_module_id) {

        pa_proplist* sink_proplist = i->proplist;
        eprintf("sink\n");
        eprintf("sink str: %s\n", i->name);
        eprintf("sink idx: %d\n", i->index);
        //printf("sink description: %s\n", i->description);
        int err = pa_proplist_sets(
            sink_proplist, PA_PROP_DEVICE_DESCRIPTION, "TEST AUDIO SINK"
        );
        eprintf("sink: \n");
        eprintf("%s", pa_proplist_to_string(sink_proplist));
        //printf("ppserr: %d\n", err);
        //pa_proplist_gets(sink_proplist, PA_PROP_DEVICE_DESCRIPTION));


        /* Set up stream */
        //pa_sample_spec sample_spec;
        pa_sample_spec sample_spec = i->sample_spec;
        //sample_spec.channels = 2;
        //sample_spec.rate = 32000;
        //sample_spec.format = PA_SAMPLE_S16LE;

        char samplebuf[1024];
        pa_sample_spec_snprint(samplebuf, 1024, &(i->sample_spec));
        eprintf("sampleformat %s\n", samplebuf);
        eprintf("latency: %zu\n", i->latency);

        pa_proplist* proplist = pa_proplist_new();
        pa_proplist_set(
            proplist, PA_PROP_DEVICE_DESCRIPTION, "Test DS4 Stream", 14
        );

        pa_stream* stream = pa_stream_new_with_proplist(
            c, "STR_DS4TEST", &sample_spec, NULL, proplist
        );
        //printf("pa_stream_new() : %s\n", pa_strerror(pa_context_errno(c)));
        //printf("Streamptr: %p\n", stream);

        pa_stream_set_state_callback(stream, stream_state_cb, NULL);
        pa_stream_set_read_callback(stream, stream_read_cb, self_v);


        pa_buffer_attr buffer_attr;
        //memset(&buffer_attr, 0, sizeof(buffer_attr));
        buffer_attr.maxlength = (uint32_t) -1;
        buffer_attr.prebuf = (uint32_t) -1;
        buffer_attr.fragsize = (uint32_t) -1;
        buffer_attr.tlength = (uint32_t) -1;
        buffer_attr.minreq = (uint32_t) -1;
        //buffer_attr.maxlength = (uint32_t) -1;
        //buffer_attr.prebuf = (uint32_t) 12*data_per_sbc_frame;
        //buffer_attr.fragsize = (uint32_t) data_per_sbc_frame;
        //buffer_attr.tlength = (uint32_t) data_per_sbc_frame;
        buffer_attr.fragsize = pa_usec_to_bytes(50, &sample_spec);
        //buffer_attr.minreq = (uint32_t) data_per_sbc_frame;

        pa_stream_flags_t flags = PA_STREAM_ADJUST_LATENCY;

        //printf("in %s\n", i->name);
        char device_strbuf[1024];
        snprintf(device_strbuf, 1024, "%s.monitor", i->name);
        //printf("inm: %s\n", device_strbuf);
        int screrr = pa_stream_connect_record(
            stream, device_strbuf, &buffer_attr, flags
        );
        //printf("screrr %d\n", screrr);
        //printf(
        //    "pa_stream_connect_record(): %s\n",
        //    pa_strerror(pa_context_errno(c))
        //);

        pa_stream_trigger(stream, stream_success_cb, NULL);

        pa_stream_set_overflow_callback(stream, stream_overflow_cb, NULL);
        pa_stream_set_underflow_callback(stream, stream_underflow_cb, NULL);
    }
}

void PulseaudioSBCStream::module_cb(pa_context* c, uint32_t idx, void* self_v) {
    eprintf("PulseaudioSBCStream module_cb\n");
    Self* self = static_cast<Self*>(self_v);
    //printf("Module_cb: %d\n", idx);
    self->sink_module_id = idx;
    eprintf("Sink idx %d\n", idx);

    //return;

    pa_context_get_sink_info_list(
        c, sink_info_cb, self_v
    );

    eprintf("PulseaudioSBCStream module_cb done\n");
}

void PulseaudioSBCStream::state_cb(pa_context* c, void* self_v) {
    eprintf("PulseaudioSBCStream state_cb\n");
    //printf("Context changed\n");

    if(pa_context_get_state(c) == PA_CONTEXT_READY) {

        Self* self = static_cast<Self*>(self_v);

        char options_buf[1024];
        snprintf(
            options_buf, 1024,
            "sink_name=\"%s\" rate=\"%d\" "
            "sink_properties=device.description=\"%s\"",
            self->sink_name.c_str(), 32000, self->sink_description.c_str()
        );
        eprintf("Module opts: %s\n", options_buf);
        pa_context_load_module(
            c, "module-null-sink", options_buf, module_cb, self_v
        );
        
    }
    eprintf("PulseaudioSBCStream state_cb done\n");
}

void PulseaudioSBCStream::unload_module_success(pa_context* c, int success, void* self_v) {
    eprintf("PulseaudioSBCStream unload_module_success\n");
    //pa_threaded_mainloop_api* api = api_v;
    Self* self = static_cast<Self*>(self_v);

    //pa_mainloop_quit(self->mainloop, 20);

    pa_threaded_mainloop_get_api(self->mainloop)->quit(
        pa_threaded_mainloop_get_api(self->mainloop), 20
    );
    eprintf("PulseaudioSBCStream unload_module_success done\n");
}

void PulseaudioSBCStream::mainloop_sigint_handler(
    pa_mainloop_api* api, pa_signal_event* e, int sig, void* self_v
) {
    eprintf("PulseaudioSBCStream mainloop_sigint_handler\n");
    Self* self = static_cast<Self*>(self_v);

    pa_signal_free(e);

    self->stop();
    eprintf("PulseaudioSBCStream mainloop_sigint_handler done\n");
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
    eprintf("PulseaudioSBCStream init\n");

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
    pa_context_set_state_callback(c, state_cb, this);

    eprintf("PulseaudioSBCStream init done\n");
}

PulseaudioSBCStream::~PulseaudioSBCStream() {
    eprintf("PulseaudioSBCStream destructor");
    pa_context_disconnect(this->context);

    sbc_finish(&(this->audio_loop_sbc));

    eprintf("PulseaudioSBCStream destructor done");
}

void PulseaudioSBCStream::run() {
    eprintf("PulseaudioSBCStream run\n");

    //pa_signal_init(pa_threaded_mainloop_get_api(this->mainloop));
    //pa_signal_new(SIGINT, mainloop_sigint_handler, this);

    int ml_return;
    //int err = pa_threaded_mainloop_run(this->mainloop, &ml_return);
    int err = pa_threaded_mainloop_start(this->mainloop);

    eprintf("err: %d\n", err);
    eprintf("returned %d\n", ml_return);
    eprintf("PulseaudioSBCStream run done\n");
}

void PulseaudioSBCStream::stop() {
    eprintf("PulseaudioSBCStream stop\n");
    if(this->sink_module_id > 0) {
        eprintf("trying unload module\n");
        pa_context_unload_module(
            this->context, this->sink_module_id,
            unload_module_success, this
        );
    } else {
        unload_module_success(this->context, 0, this);
    }
    eprintf("PulseaudioSBCStream stop done\n");
}
