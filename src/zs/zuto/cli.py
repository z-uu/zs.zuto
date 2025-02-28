import click
from zs.zuto.scheduler import ZutoScheduler
import time


@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def zuto(path):
    scheduler = ZutoScheduler(path)
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    zuto()
