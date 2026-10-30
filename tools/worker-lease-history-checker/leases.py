"""Check supplied lease histories at an explicit as-of ordinal; never collect a live clock."""
import toolkit as t
import decision_core as c
import worker_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','items','lease_events','as_of'});t.require(v['format']=='outlands-worker-leases-v1','FORMAT_INVALID');t.integer(v['as_of'],10**12)
    counts={};issues=[];items,events,assessment,windows,qualified=r.lease_scope(v['items'],v['lease_events'],v['as_of'],counts,issues)
    return r.output(raw,'outlands-worker-leases-report-v1',counts,issues,qualified,assessment,dict(items_sha256=c.cohort_pin(items),lease_events_sha256=c.cohort_pin(events),as_of_sha256=c.pin(v['as_of'])),as_of=v['as_of'])

def main(argv=None):return c.cli('Check declared worker leases; no clock, worker access or ownership changes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
