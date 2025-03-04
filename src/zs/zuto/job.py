import typing
import yaml
from dataclasses import dataclass, field
from functools import cached_property
from zs.zuto.ctx import ZutoCtx
import uuid
import os
from zuu.util_timeparse import time_parse
from zs.zuto.builtin import Builtin
import threading
from zs.zuto.utils import lifetime
from zuu.util_procLifetime import cleanup
import subprocess

_job_map = {}


@dataclass(init=False)
class ZutoJob:

    name: str
    id: str = None
    description: typing.Optional[str] = None
    cleanup: bool = False
    lifetime: typing.Optional[str] = None
    when: typing.Optional[str] = None
    steps: typing.List[typing.Union[dict, str]] = field(default_factory=list)

    @cached_property
    def whened(self):
        if self.when:
            parsed = time_parse(self.when)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def __init__(self, ctx: ZutoCtx, _path: str, **kwargs):
        # Initialize all dataclass fields manually
        self.name = kwargs["name"]
        self.id = kwargs.get("id")
        self.description = kwargs.get("description")
        self.when = kwargs.get("when")
        self.steps = kwargs.get("steps", [])
        self.lifetime = kwargs.get("lifetime", None)
        self.cleanup = kwargs.get("cleanup", False)

        # Then set other properties
        self._ctx = ctx
        self._path = os.path.abspath(_path)
        self.id = _job_map.get(self._path, self.id or str(uuid.uuid4()))

        if self._path not in _job_map:
            _job_map[self._path] = self.id

        self.whened
        self.lifetimed

    @cached_property
    def lifetimed(self):
        if self.lifetime:
            return time_parse(self.lifetime)
        return None


    def _handle_dict(self, step: dict):
        cmd_pair = step.popitem()
        cmd = cmd_pair[0]
        fv = cmd_pair[1]
        if cmd in dir(Builtin):
            getattr(Builtin, cmd)(fv, **step)
        elif cmd in self._ctx.funcMaps:
            self._ctx.funcMaps[cmd](fv, **step)
        else:
            raise ValueError(f"Unknown command: {cmd}")

    def _execute(self):
        try:
            print(f"Name: {self.name}")

            for step in self.steps:
                if isinstance(step, dict):
                    step_copy = step.copy()
                    self._handle_dict(step_copy)
                elif isinstance(step, str):
                    print(f"Step: {step[:40]}...")
                    res = subprocess.Popen(
                        step,
                        shell=True,
                    )
                    res.wait()
                    if res.returncode != 0:
                        print(f"Step {step} failed with return code {res.returncode}")
                        return
        except KeyboardInterrupt:
            print("\nJob execution interrupted by user")
            # Clean up any running subprocesses
            if 'res' in locals():
                res.terminate()
                res.wait()

    def execute(self):
        self._ctx.currentlyRunning = self

        # Create the base function to decorate
        func_to_decorate = self._execute
        if self.lifetime:
            func_to_decorate = lifetime(self.lifetime)(func_to_decorate)
        if self.cleanup:
            func_to_decorate = cleanup(windows=True, processes=True, new_only=True)(
                func_to_decorate
            )
        # Execute in a separate thread
        thread = threading.Thread(target=func_to_decorate)
        thread.start()
        thread.join()

        self._ctx.currentlyRunning = None

    @classmethod
    def from_file(cls, path: str, ctx: ZutoCtx):
        with open(path, "r", encoding="utf-8") as f:
            yamldata = yaml.safe_load(f)

        return cls(ctx, path, **yamldata)
