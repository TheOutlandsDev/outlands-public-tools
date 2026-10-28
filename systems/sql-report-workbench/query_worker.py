"""Private pipe protocol for an owned child; not an operating-system sandbox."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sql_report.engine import main
if __name__=='__main__':main()
