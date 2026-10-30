"""Calculate exact squared-probability error on one explicit complete cohort."""
import toolkit as t
import decision_core as c
import probability_core as p

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','contract','cohort','predictions','outcomes'})
    t.require(value['format']=='outlands-binary-probability-error-v1','FORMAT_INVALID')
    counts={};issues=[];evaluation,_=p.evaluation(value,counts,issues)
    return p.output(raw,'outlands-binary-probability-error-report-v1',counts,issues,**evaluation)

def main(argv=None):return c.cli('Describe exact squared-probability error; no fitting, thresholds or truth checks.',check,argv)
if __name__=='__main__':raise SystemExit(main())
