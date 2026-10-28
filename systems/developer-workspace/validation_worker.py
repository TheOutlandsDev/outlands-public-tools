"""Owned validation child; no project import, eval, exec or command execution."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from developer.source_validation import main
if __name__=='__main__':main()
