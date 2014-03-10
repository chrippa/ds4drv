class Backend(object):
    """The backend is responsible for finding and creating DS4 devices."""

    __name__ = "backend"

    def __init__(self, manager):
        self.logger = manager.new_module(self.__name__)

    def setup(self):
        """Initialize the backend and make it ready for scanning.

        Raises BackendError on failure.
        """

        raise NotImplementedError

    @property
    def devices(self):
        """This iterator yields any devices found."""

        raise NotImplementedError
