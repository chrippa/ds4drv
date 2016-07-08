class SBCHeaders(object):

    MONO = 0
    DUAL_CHANNEL = 1
    STEREO = 2
    JOINT_STEREO = 3


    def __init__(
        self,
        sampling_frequency = 32000,
        bitpool = 50,
        channel_mode = None,
        nrof_blocks = 16,
        nrof_subbands = 8
    ):
        if channel_mode == None:
            channel_mode = SBCHeaders.STEREO

        self.syncword = 156

        self.nrof_subbands = nrof_subbands
        self.channel_mode = channel_mode
        self.nrof_channels = 2
        if self.channel_mode == SBCHeaders.MONO:
            self.nrof_channels = 1
        self.nrof_blocks = nrof_blocks
        self.join = 0
        if self.channel_mode == SBCHeaders.JOINT_STEREO:
            self.join = 1
        self.bitpool = bitpool
        self.sampling_frequency = sampling_frequency


        self.frame_length = None
        self.bitrate = None


    def calculate_frame_length(self):
        # Calculate frame length
        def ceildiv(a, b):
            return -(-a // b)

        if (
            (self.channel_mode == SBCHeaders.MONO)
            or (self.channel_mode ==
                SBCHeaders.DUAL_CHANNEL)
        ):

            self.frame_length = (
                4 + (
                    4
                        * self.nrof_subbands
                        * self.nrof_channels
                )//8
                + ceildiv(
                    self.nrof_blocks
                        * self.nrof_channels
                        * self.bitpool,
                    8
                )
            )
        else:
            self.frame_length = (
                4 + (
                    4
                        * self.nrof_subbands
                        * self.nrof_channels
                )//8
                + ceildiv(
                    self.join
                        * self.nrof_subbands
                    + self.nrof_blocks
                        * self.bitpool,
                    8
                )
            )

        return self.frame_length


    def calculate_bit_rate(self):
        if self.frame_length == None:
            self.calculate_frame_length()

        # Calculate bit rate
        self.bit_rate = (
            8 * self.frame_length * self.sampling_frequency
                // self.nrof_subbands // self.nrof_blocks
        )

        return self.bit_rate


    def parse_header(self, raw_header):
        # Info in SBC headers from
        # https://tools.ietf.org/html/draft-ietf-avt-rtp-sbc-01#section-6.3

        # Syncword should be 0x9C
        self.syncword = raw_header[0]

        self.nrof_subbands = \
            SBCHeaders.parse_number_of_subbands(
                raw_header
            )
        self.channel_mode = SBCHeaders.parse_channel_mode(
            raw_header
        )
        self.nrof_channels = 2
        if self.channel_mode == SBCHeaders.MONO:
            self.nrof_channels = 1
        self.nrof_blocks = SBCHeaders.parse_number_of_blocks(
            raw_header
        )
        self.join = 0
        if self.channel_mode == SBCHeaders.JOINT_STEREO:
            self.join = 1
        self.nrof_subbands = \
            SBCHeaders.parse_number_of_subbands(
                raw_header
            )
        self.bitpool = SBCHeaders.parse_bitpool(raw_header)
        self.sampling_frequency = SBCHeaders.parse_sampling(
            raw_header
        )


    def print_values(self):
        # Info in SBC headers from
        # https://tools.ietf.org/html/draft-ietf-avt-rtp-sbc-01#section-6.3

        print("syncword: ", self.syncword)

        print("nrof_subbands", self.nrof_subbands)
        print("channel_mode", [
            "MONO", "DUAL_CHANNEL", "STEREO", "JOINT_STEREO"
            ][self.channel_mode]
        )
        print("nrof_channels", self.nrof_channels)
        print("nrof_blocks", self.nrof_blocks)
        print("join: ", self.join)
        print("nrof_subbands", self.nrof_subbands)
        print("bitpool", self.bitpool)
        print("sampling_frequency", self.sampling_frequency)
        print("frame_length", self.frame_length)
        print("bit_rate", self.bit_rate)


    @staticmethod
    def parse_sampling(raw_header):

        sf_word = raw_header[1]

        # Find sampling frequency from rightmost 2 bits
        if sf_word & 0x80 == 0x80:
            bit_0 = 1
        else:
            bit_0 = 0

        if sf_word & 0x40 == 0x40:
            bit_1 = 1
        else:
            bit_1 = 0

        if (bit_0 == 0) and (bit_1 == 0):
            sampling_frequency = 16000
        elif (bit_0 == 0) and (bit_1 == 1):
            sampling_frequency = 32000
        elif (bit_0 == 1) and (bit_1 == 0):
            sampling_frequency = 44100
        elif (bit_0 == 1) and (bit_1 == 1):
            sampling_frequency = 48000

        return sampling_frequency


    @staticmethod
    def parse_number_of_blocks(raw_header):

        nb_word = raw_header[1]

        if nb_word & 0x20 == 0x20:
            bit_0 = 1
        else:
            bit_0 = 0

        if nb_word & 0x10 == 0x10:
            bit_1 = 1
        else:
            bit_1 = 0


        if (bit_0 == 0) and (bit_1 == 0):
            number_of_blocks = 4
        elif (bit_0 == 0) and (bit_1 == 1):
            number_of_blocks = 8
        elif (bit_0 == 1) and (bit_1 == 0):
            number_of_blocks = 12
        elif (bit_0 == 1) and (bit_1 == 1):
            number_of_blocks = 16

        return number_of_blocks


    @staticmethod
    def parse_channel_mode(raw_header):

        ch_word = raw_header[1]

        if ch_word & 0x08 == 0x08:
            bit_0 = 1
        else:
            bit_0 = 0

        if ch_word & 0x04 == 0x04:
            bit_1 = 1
        else:
            bit_1 = 0

        if (bit_0 == 0) and (bit_1 == 0):
            channel_mode = SBCHeaders.MONO
        elif (bit_0 == 0) and (bit_1 == 1):
            channel_mode = SBCHeaders.DUAL_CHANNEL
        elif (bit_0 == 1) and (bit_1 == 0):
            channel_mode = SBCHeaders.STEREO
        elif (bit_0 == 1) and (bit_1 == 1):
            channel_mode = SBCHeaders.JOINT_STEREO

        return channel_mode


    @staticmethod
    def parse_number_of_subbands(raw_header):
        if raw_header[1] & 0x01 == 0x01:
            number_of_subbands = 8
        else:
            number_of_subbands = 4

        return number_of_subbands


    @staticmethod
    def parse_bitpool(raw_header):
        return int(raw_header[2])
