from zs.zuto.scheduler import ZutoScheduler
import time

path = "www"

scheduler = ZutoScheduler(path)
scheduler.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.shutdown()