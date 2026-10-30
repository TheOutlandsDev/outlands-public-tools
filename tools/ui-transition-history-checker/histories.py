"""Offline custom histories contracts; supplied declarations only."""
import decision_core as c
import form_core as r
def check(raw):return r.check(raw,'histories')
def main(argv=None):return c.cli("Check supplied histories declarations; no browser, scripts or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
