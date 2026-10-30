"""Offline custom forms contracts; supplied declarations only."""
import decision_core as c
import form_core as r
def check(raw):return r.check(raw,'forms')
def main(argv=None):return c.cli("Check supplied forms declarations; no browser, scripts or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
