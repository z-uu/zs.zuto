from time import sleep
import os

class Builtin:
    @staticmethod
    def sleep(x : str):
        sleep(int(x))
    
    @staticmethod
    def setenv(x : str):
        k, v = x.split("=", 1)
        os.environ[k] = v


