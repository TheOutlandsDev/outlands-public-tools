"""Original MIT generated launcher fixtures; no real application data."""
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


class FakeChild:
    def __init__(self, events, failure=None, read_mask=None, priority=0x20, resume_count=1,
                 completed=True, exit_status=0, terminate_fails=False, failure_details=None,
                 close_fails=False):
        self.events = events
        self.failure = failure
        self.read_mask = read_mask
        self.priority = priority
        self.resume_count = resume_count
        self.completed = completed
        self.exit_status = exit_status
        self.terminate_fails = terminate_fails
        self.failure_details = failure_details
        self.close_fails = close_fails
        self.pid = 4242
        self.mask = 0xff

    def _call(self, name):
        self.events.append(name)
        if self.failure == name:
            from app_affinity import AffinityError
            raise AffinityError("Generated fixture failure", self.failure_details)

    def set_mask(self, mask):
        self._call("set_mask")
        self.mask = mask

    def get_mask(self):
        self._call("get_mask")
        return self.mask if self.read_mask is None else self.read_mask

    def get_priority(self):
        self._call("get_priority")
        return self.priority

    def resume(self):
        self._call("resume")
        return self.resume_count

    def wait(self, seconds):
        self._call("wait")
        return self.completed

    def exit_code(self):
        self._call("exit_code")
        return self.exit_status

    def terminate(self):
        self.events.append("terminate")
        if self.terminate_fails:
            from app_affinity import AffinityError
            raise AffinityError("Generated cleanup failure")

    def close(self):
        self.events.append("close")
        if self.close_fails:
            from app_affinity import AffinityError
            raise AffinityError("Generated close failure", {"handle_close_errors": [6]})


class FakeBackend:
    def __init__(self, available_mask=0xff, pointer_bits=64, processor_groups=1,
                 pids=(), unqueryable=0, truncated=False, child_options=None, create_fails=False,
                 reject_paths=False):
        self.available_mask = available_mask
        self.pointer_bits = pointer_bits
        self.processor_groups = processor_groups
        self.pids = list(pids)
        self.unqueryable = unqueryable
        self.truncated = truncated
        self.child_options = child_options or {}
        self.create_fails = create_fails
        self.reject_paths = reject_paths
        self.events = []
        self.child = None
        self.created_plan = None

    def capabilities(self):
        self.events.append("capabilities")
        return {"available_mask": self.available_mask, "system_mask": 0xff,
                "pointer_bits": self.pointer_bits, "processor_groups": self.processor_groups}

    def verify_local_paths(self, executable, cwd):
        self.events.append("verify_local_paths")
        if self.reject_paths:
            from app_affinity import AffinityError
            raise AffinityError("Generated mapped-network-drive refusal")

    def duplicates(self, executable):
        self.events.append("duplicates")
        return {"pids": list(self.pids), "unqueryable": self.unqueryable, "truncated": self.truncated}

    def create(self, plan):
        self.events.append("create")
        if self.create_fails:
            from app_affinity import AffinityError
            raise AffinityError("Generated creation failure")
        self.created_plan = plan
        self.child = FakeChild(self.events, **self.child_options)
        return self.child


def make_executable(folder):
    path = Path(folder) / "fictional app.exe"
    path.write_bytes(b"Generated placeholder. Used by fake backend only.\n")
    return path


def cli(*arguments, env_extra=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-B", "-m", "app_affinity", *arguments],
                          cwd=ROOT, env=env, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=30)


def receipt(result):
    if result.returncode:
        raise AssertionError(f"Fixture launcher failed: {result.returncode}; {result.stderr}")
    return json.loads(result.stdout)
