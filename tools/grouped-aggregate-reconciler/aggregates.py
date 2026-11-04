"""Offline grouped report aggregates checks."""
import decision_core as c
import group_core as g
def check(raw):return g.check(raw,'aggregates')
def main(argv=None):return c.cli('Check supplied grouped report aggregates.',check,argv)
if __name__=='__main__':raise SystemExit(main())
