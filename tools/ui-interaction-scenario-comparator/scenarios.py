"""Offline custom scenarios contracts; supplied declarations only."""
import decision_core as c
import form_core as r
def check(raw):return r.check(raw,'scenarios')
def main(argv=None):return c.cli("Check supplied scenarios declarations; no browser, scripts or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
