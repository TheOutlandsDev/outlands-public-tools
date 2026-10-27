"""Disposable fictional workspaces, always outside publication source."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from data_services.contracts import canonical, fictional_configuration, fictional_input
from data_services.service import Stack


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-stack-", dir=os.environ.get("OUTLANDS_TEST_TEMP"))
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "workspace"

    def create(self, *, run=False):
        Stack.initialize(self.root)
        with Stack(self.root) as app:
            app.configure(fictional_configuration())
            if run:
                app.run("sample", "notice", fictional_input())

    def hashes(self):
        import hashlib
        return {p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file()}
