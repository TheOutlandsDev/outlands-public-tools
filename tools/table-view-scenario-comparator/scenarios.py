"""Offline typed view declarations; no database, browser or target actions."""
import decision_core as c
import view_core as r
def check(raw):return r.check(raw,'scenarios')
def main(argv=None):return c.cli("Check supplied view declarations; no SQL, browser or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
