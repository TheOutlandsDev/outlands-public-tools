"""Describe exact field-metadata changes without printing raw setting/default values."""
import toolkit as t
import decision_core as c
import config_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','baseline','candidate'});t.require(v['format']=='outlands-config-contract-diff-v1','FORMAT_INVALID')
    counts={};issues=[];baseline=r.contract(v['baseline'],'baseline',counts,issues);candidate=r.contract(v['candidate'],'candidate',counts,issues)
    if (baseline['id'],baseline['revision'])==(candidate['id'],candidate['revision']) and c.pin(baseline)!=c.pin(candidate):c.issue(issues,'contracts',0,'CONTRACT_IDENTITY_CONFLICT')
    qualified=not issues;assessment=None
    if qualified:
        before={row['id']:row for row in baseline['fields']};after={row['id']:row for row in candidate['fields']};out=[]
        for key in sorted(set(before)|set(after)):
            if key not in before:state='added';attributes=[]
            elif key not in after:state='removed';attributes=[]
            else:
                attributes=[field for field in ('type','required','default_sha256','constraint_sha256') if before[key][field]!=after[key][field]];state='changed' if attributes else 'unchanged'
            if state!='unchanged':c.issue(issues,'fields',0,'FIELD_'+state.upper())
            out.append(dict(id=key,state=state,changed_attributes=attributes))
        assessment=dict(fields=out,header_changed=(baseline['id'],baseline['revision'])!=(candidate['id'],candidate['revision']),all_field_metadata_equal=not issues,breaking_change_inferred=False)
    return r.output(raw,'outlands-config-contract-diff-report-v1',counts,issues,qualified,assessment,dict(baseline_sha256=c.pin(baseline),candidate_sha256=c.pin(candidate)))

def main(argv=None):return c.cli('Compare declared configuration contracts; no values or compatibility inference.',check,argv)
if __name__=='__main__':raise SystemExit(main())
