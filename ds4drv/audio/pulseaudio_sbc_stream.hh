#include <string>
#include <vector>
#include <set>
#include <functional>
#include <memory>

#include <mutex>
#include <atomic>

#include <pulse/context.h>
#include <pulse/thread-mainloop.h>
#include <pulse/stream.h>
#include <pulse/introspect.h>
#include <pulse/mainloop-signal.h>

#include <sbc/sbc.h>

class PulseaudioSBCStream {
private:
    std::mutex sbc_frame_buffer_mutex;
    std::atomic<bool> sbc_frames_waiting_flag;

public:
    typedef PulseaudioSBCStream Self; 

    typedef std::function<
        void (
            sbc_t* sbc, void* sbc_frame, size_t length
        )
    > ReadSBCFrameCallback;

    pa_context* context;
    pa_threaded_mainloop* mainloop;

    std::string sink_name;
    std::string sink_description;
    uint32_t sink_module_id;

    sbc_t audio_loop_sbc;
    std::vector<char> audio_buffer;

    typedef std::set<int> FDList;
    FDList fds;

    void add_fd(int fd);
    void remove_fd(int fd);


    static void stream_read_cb(
        pa_stream *s, std::size_t length, void *self_v
    );

    static void stream_state_cb(pa_stream *s, void *self_v);


    static void stream_success_cb(
        pa_stream *s, int success, void* self_v
    );

    static void stream_overflow_cb(pa_stream* p, void* self_v);

    static void stream_underflow_cb(pa_stream* p, void* self_v);

    static void sink_info_cb(
        pa_context* c, const pa_sink_info* i, int eol, void* self_v
    );

    static void module_cb(pa_context* c, uint32_t idx, void* self_v);

    static void state_cb(pa_context* c, void* self_v);

    static void unload_module_success(pa_context* c, int success, void* self_v);

    static void mainloop_sigint_handler(
        pa_mainloop_api* api, pa_signal_event* e, int sig, void* self_v
    );

    PulseaudioSBCStream(
        std::string sink_name,
        std::string sink_description
    );

    ~PulseaudioSBCStream();

    void run();

    void stop();
};
