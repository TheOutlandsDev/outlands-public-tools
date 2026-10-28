"""Run fictional standard-library tests; browser tests are a separate acceptance gate."""
from pathlib import Path
import sys
import unittest
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests')))
    sys.exit(not result.wasSuccessful())
