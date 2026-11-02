"""Offline supplied navigation declarations; no browser or target actions."""
import decision_core as c
import navigation_core as r
def check(raw):return r.check(raw,'scenarios')
def main(argv=None):return c.cli("Check supplied navigation declarations; no browser, network or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
