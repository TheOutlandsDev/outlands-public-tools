"""Run portable checks and require relevant native cases in CI."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"tests"))
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/"tests")))
allowed = {"test_posix_fifo_is_refused_without_blocking"} if os.name=="nt" else {"test_windows_junction_and_stream_names_are_refused"}
unexpected = os.environ.get("STACK_REQUIRE_LINKS")=="1" and any(test._testMethodName not in allowed for test,reason in result.skipped)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun==65 and not unexpected else 1)
