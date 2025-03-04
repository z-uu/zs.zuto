from time import sleep
import os


class Builtin:
    @staticmethod
    def sleep(x: str):
        from zuu.util_timeparse import time_parse
        import datetime
        sleep_till = time_parse(x)
        elapsed = sleep_till - datetime.datetime.now()
        sleep(elapsed.total_seconds())

    @staticmethod
    def setenv(x: str):
        k, v = x.split("=", 1)
        os.environ[k] = v
