"""Run fictional application checks, requiring native link fixtures in CI."""
from pathlib import Path
import sys
import unittest

if __name__=='__main__':
    # Keep platform limitations visible in unittest's final summary.
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
