"""Offline custom submissions contracts; supplied declarations only."""
import decision_core as c
import form_core as r
def check(raw):return r.check(raw,'submissions')
def main(argv=None):return c.cli("Check supplied submissions declarations; no browser, scripts or target changes.",check,argv)
if __name__=="__main__":raise SystemExit(main())
