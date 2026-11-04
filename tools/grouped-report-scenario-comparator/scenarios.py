"""Offline grouped report scenarios checks."""
import decision_core as c
import group_core as g
def check(raw):return g.check(raw,'scenarios')
def main(argv=None):return c.cli('Check supplied grouped report scenarios.',check,argv)
if __name__=='__main__':raise SystemExit(main())
