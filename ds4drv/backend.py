class Backend(object):
    __name__ = "backend"

    def __init__(self, manager):
        self.logger = manager.new_module(self.__name__)

    def setup(self):
        raise NotImplementedError

    @property
    def devices(self):
        raise NotImplementedError
