import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job
from apscheduler.executors.pool import ThreadPoolExecutor
from zs.zuto.ctx import ZutoCtx
from zs.zuto.job import ZutoJob
from zuu.stdext_importlib import import_file
from zs.zuto.utils import gather_zuto_mods
from datetime import datetime


class ZutoScheduler:
    def __init__(
        self,
        path: str,
        exclude_parsing_py: bool = False,
        exclude_parsing_mod: bool = False,
        ctx: ZutoCtx | None = None,
    ):
        path = os.path.abspath(path)  # Convert to absolute path first
        assert os.path.exists(path), f"Path {path} does not exist"
        assert os.path.isdir(path), f"Path {path} is not a directory"
        os.chdir(path)
        self.scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=1)}
        )
        self.observer = Observer()
        self.event_handler = FileHandler(self)
        self.observer.schedule(
            self.event_handler, path, recursive=True
        )  # Now using absolute path
        self.jobs = {}
        self.ctx = ctx or ZutoCtx(self)
        if not ctx and not exclude_parsing_mod:
            self.ctx.funcMaps.update(
                gather_zuto_mods(os.path.dirname(os.path.abspath(__file__)))
            )
            self.ctx.funcMaps.update(
                gather_zuto_mods(
                    os.path.join(
                        os.path.dirname(os.path.dirname(sys.executable)),
                        "Lib",
                        "site-packages",
                        "zs",
                        "zuto",
                    )
                )
            )

        self.path = path

        # parse current folder for jobs
        for file in os.listdir(path):
            if file.endswith(".yml") or file.endswith(".yaml"):
                self.add_job(
                    file, ZutoJob.from_file(os.path.join(path, file), self.ctx)
                )
            elif file.endswith(".py") and not exclude_parsing_py:
                mod = import_file(file, "zs.zuto.funcs")
                eligibles = [name for name in dir(mod.Cmds) if not name.startswith("_")]
                for name in eligibles:
                    if name in self.ctx.funcMaps:
                        print(
                            f"Warning: Function {name} already exists in ctx.funcMaps"
                        )
                        continue
                    self.ctx.funcMaps[name] = getattr(mod.Cmds, name)

    def add_job(self, job_id, zuto_job):
        """Add or replace a job in the scheduler"""
        existing_job: Job | None = self.scheduler.get_job(job_id)
        if existing_job and self.ctx.currentlyRunning is not existing_job:
            existing_job.remove()

        # Check if the job's scheduled time has passed
        scheduled_time = datetime.strptime(zuto_job.whened, "%Y-%m-%d %H:%M:%S")
        if scheduled_time < datetime.now():
            print(f"Job {job_id} was scheduled for {zuto_job.whened} which has passed. Queuing for execution.")
            # Create a chain of jobs using APScheduler's own sequencing
            if not hasattr(self, '_missed_jobs_queue'):
                self._missed_jobs_queue = []
                # Schedule the first missed job immediately
                self._schedule_next_missed()
            self._missed_jobs_queue.append((job_id, zuto_job))
            return

        print(f"Scheduled task {job_id} to run at {zuto_job.whened}")
        self.scheduler.add_job(
            zuto_job.execute, 
            trigger="date", 
            run_date=zuto_job.whened, 
            id=job_id
        )

    def _schedule_next_missed(self):
        """Schedule the next missed job using APScheduler's event system"""
        if not hasattr(self, '_missed_jobs_queue') or not self._missed_jobs_queue:
            return

        job_id, zuto_job = self._missed_jobs_queue.pop(0)
        print(f"Scheduling missed job {job_id} for immediate execution")
        
        job = self.scheduler.add_job(
            zuto_job.execute,
            trigger='date',
            run_date=datetime.now(),
            id=f'_missed_{job_id}'
        )
        
        # Add listener for when the job completes
        job.add_listener(
            lambda event: self._schedule_next_missed() if event.code == 4096 else None,
            mask=4096  # EVENT_JOB_EXECUTED code
        )

    def start(self):
        """Start both scheduler and file observer"""
        self.scheduler.start()
        self.observer.start()

    def shutdown(self):
        """Graceful shutdown of all components"""
        self.observer.stop()
        self.observer.join()
        self.scheduler.shutdown()


class FileHandler(FileSystemEventHandler):
    def __init__(self, scheduler: ZutoScheduler):
        super().__init__()
        self.scheduler = scheduler

    def on_modified(self, event):
        if event.is_directory or not event.src_path.startswith(self.scheduler.path):
            return

        if not event.src_path.endswith(".yml") and not event.src_path.endswith(".yaml"):
            return

        print(f"Detected change in {event.src_path}")
        try:
            zuto_job = ZutoJob.from_file(event.src_path, self.scheduler.ctx)
            self.scheduler.add_job(zuto_job.id, zuto_job)
        except Exception as e:
            print(f"Error adding job {event.src_path}: {e}")
