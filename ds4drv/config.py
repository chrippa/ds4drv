import re

try:
    import ConfigParser as configparser
except ImportError:
    import configparser


class Config(object):
    def __init__(self):
        self.config = configparser.SafeConfigParser()

    def load(self, filename):
        self.config.read([filename])

    def section_to_args(self, section):
        args = []

        for key, value in self.section(section).items():
            if value.lower() == "true":
                args.append("--{0}".format(key))
            elif value.lower() == "false":
                pass
            else:
                args.append("--{0}={1}".format(key, value))

        return args

    def section(self, section, key_type=str, value_type=str):
        try:
            # Removes empty values and applies types
            return dict(map(lambda kv: (key_type(kv[0]), value_type(kv[1])),
                            filter(lambda i: bool(i[1]),
                                   self.config.items(section))))
        except configparser.NoSectionError:
            return {}

    def sections(self, prefix):
        for section in self.config.sections():
            match = re.match(r"{0}:(.+)".format(prefix), section)
            if match:
                yield match.group(1), section

    def controllers(self):
        controller_sections = dict(self.sections("controller"))
        if not controller_sections:
            return ["--next-controller"]

        last_controller = max(map(lambda c: int(c[0]), controller_sections))
        args = []
        for i in range(1, last_controller + 1):
            section = controller_sections.get(str(i))
            if section:
                for arg in self.section_to_args(section):
                    args.append(arg)

            args.append("--next-controller")

        return args
