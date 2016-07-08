#include <string>
#include <vector>
#include <set>
#include <functional>
#include <memory>

#include <mutex>
#include <atomic>

#include <boost/circular_buffer.hpp>

#include <pulse/context.h>
#include <pulse/thread-mainloop.h>
#include <pulse/stream.h>
#include <pulse/introspect.h>
#include <pulse/mainloop-signal.h>

#include <sbc/sbc.h>

class PulseaudioSBCStream {
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
    boost::circular_buffer<unsigned char> audio_buffer;

    typedef std::set<int> FDList;
    FDList fds;

    void add_fd(int fd);
    void remove_fd(int fd);


    static void read_pulse_stream(
        pa_stream *s, std::size_t length, void *self_v
    );

    static void setup_pulse_stream(
        pa_context* c, const pa_sink_info* i, int eol, void* self_v
    );

    static void module_setup_cb(pa_context* c, uint32_t idx, void* self_v);

    static void context_state_cb(pa_context* c, void* self_v);

    static void unload_module_success(pa_context* c, int success, void* self_v);

    PulseaudioSBCStream(
        std::string sink_name,
        std::string sink_description
    );

    ~PulseaudioSBCStream();

    int setup_context();

    void run();

    void stop();
};
