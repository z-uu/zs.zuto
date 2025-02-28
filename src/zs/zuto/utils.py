
import ctypes
import datetime
import threading
from functools import wraps
from zuu.util_timeparse import time_parse


def lifetime(
    timestr: str,
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get target termination time and ensure it's a timestamp
            target_time : datetime.datetime = time_parse(timestr)
            print(target_time)
            result = [None]
            exception = [None]
            thread_id = None

            def async_raise(target_tid, exc_type):
                """Raises an exception in the target thread"""
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(target_tid),
                    ctypes.py_object(exc_type)
                )
                if res == 0:
                    raise ValueError("Invalid thread ID")
                elif res != 1:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, None)
                    raise SystemError("Failed to set exception")

            def run_func():
                nonlocal thread_id
                thread_id = threading.get_ident()
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=run_func)
            thread.daemon = True
            thread.start()
            
            wait_time = max((target_time - datetime.datetime.now()).total_seconds(), 0)
            thread.join(wait_time)
            
            if thread.is_alive():
                try:
                    print(f"Lifetime expired, terminating thread {thread_id}")
                    async_raise(thread_id, SystemExit)
                    thread.join(0.1)  # Give it a moment to clean up
                except Exception:
                    pass
                return None
                
            if exception[0] is not None:
                raise exception[0]
                
            return result[0]

        return wrapper
    
    return decorator