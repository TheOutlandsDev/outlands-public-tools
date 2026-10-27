"""Run the fictional application suite; CI requires native link fixtures."""
from pathlib import Path
import sys
import unittest
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests')))
    sys.exit(not result.wasSuccessful())
