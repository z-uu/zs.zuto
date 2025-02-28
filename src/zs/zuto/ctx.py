import threading


class ZutoCtx:
    __currentlyRunning = None
    __internalLock = threading.Lock()

    __funcMaps = {}

    @property
    def funcMaps(self):
        return self.__funcMaps

    def __init__(self, scheduler):
        self.__scheduler = scheduler

    @property
    def currentlyRunning(self):
        with self.__internalLock:
            return self.__currentlyRunning

    @currentlyRunning.setter
    def currentlyRunning(self, value):
        with self.__internalLock:
            self.__currentlyRunning = value
