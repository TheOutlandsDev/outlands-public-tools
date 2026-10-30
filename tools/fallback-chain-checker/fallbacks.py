"""Check an explicit bounded fallback chain without choosing or contacting models."""
import toolkit as t
import decision_core as c
import routing_core as r

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','models','request','policy','chain'})
    t.require(value['format']=='outlands-fallback-chain-v1','FORMAT_INVALID')
    counts={};issues=[];prepared,_=r.chain_scope(value,counts,issues)
    return r.output(raw,'outlands-fallback-chain-report-v1',counts,issues,**prepared)

def main(argv=None):return c.cli('Review explicit fallback ordering and failure conditions; no dispatch.',check,argv)
if __name__=='__main__':raise SystemExit(main())
