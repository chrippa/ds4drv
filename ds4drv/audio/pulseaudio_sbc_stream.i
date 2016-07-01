%module pulseaudio_sbc_stream

/*
 * Include SWIG typemaps for std::string
*/
%include <std_string.i>
%include <cpointer.i>
%include <carrays.i>
%include <cdata.i>

/*
 * Include files and definitions to be written verbatim to _wrap.cpp
 */
%{
#include "audio/pulseaudio_sbc_stream.hh"
%}

%include "audio/pulseaudio_sbc_stream.hh"


/*
 * Make a CharArray and size_t_p type for getting SBC frame data from
 * PulseaudioSBCStream::read_sbc_frame.
 */
%pointer_class(std::size_t, size_t_p);
%array_class(unsigned char, CharArray);
