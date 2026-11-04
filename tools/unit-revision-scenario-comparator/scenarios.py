"""Offline unit scenarios checks over supplied fictional data."""
import decision_core as c
import unit_core as u
def check(raw):return u.check(raw,'scenarios')
def main(argv=None):return c.cli('Check supplied unit scenarios.',check,argv)
if __name__=='__main__':raise SystemExit(main())
