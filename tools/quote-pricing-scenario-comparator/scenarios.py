"""Offline supplied pricing declarations; no operational actions."""
import decision_core as c
import pricing_core as r
def check(raw):return r.check(raw,'scenarios')
def main(argv=None):return c.cli("Check supplied pricing declarations; no network or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
