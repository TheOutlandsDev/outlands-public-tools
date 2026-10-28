"""Real Chromium acceptance against fictional records in disposable local instances."""
from pathlib import Path
import sys
import unittest
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent/'acceptance')))
    sys.exit(not result.wasSuccessful())
