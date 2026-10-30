"""Compare explicit monotone piecewise-linear map declarations without fitting or applying them."""
import toolkit as t
import decision_core as c
import probability_core as p

def point(row):
    key,out=c.record(row,{'id','input_probability','output_probability'},('id',))
    for field in ('input_probability','output_probability'):_,out[field]=c.decimal(row[field])
    return key,out

def mapping(value,side,counts,issues):
    _,normalized=c.record(value,{'id','revision','model','model_revision','positive_label','negative_label','points'},('id','model','positive_label','negative_label'),('revision','model_revision'))
    t.require(value['positive_label']!=value['negative_label'],'LABELS_MUST_DIFFER')
    t.require(type(value['points']) is list and len(value['points'])<=64,'POINT_LIMIT')
    initial=len(issues);points=p.collect(value['points'],point,side+'_points',counts,issues)
    if len(issues)!=initial:return None,None
    ordered=sorted((row for _,row in points.values()),key=lambda r:(c.decimal(r['input_probability'])[0],r['id']))
    xs=[c.decimal(r['input_probability'])[0] for r in ordered];ys=[c.decimal(r['output_probability'])[0] for r in ordered]
    if len(ordered)<2:c.issue(issues,side,0,'MAP_POINTS_INSUFFICIENT')
    if len(set(xs))!=len(xs):c.issue(issues,side,0,'INPUT_COORDINATE_AMBIGUOUS')
    domain=bool(xs) and xs[0]==0 and xs[-1]==1
    monotone=all(a<=b for a,b in zip(ys,ys[1:]))
    if not domain:c.issue(issues,side,0,'MAP_DOMAIN_INCOMPLETE')
    if not monotone:c.issue(issues,side,0,'MAP_NOT_MONOTONE')
    normalized['points']=ordered
    return normalized,dict(points=ordered,points_count=len(ordered),domain_complete=domain,nondecreasing=monotone)

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','before','after'})
    t.require(value['format']=='outlands-calibration-map-v1','FORMAT_INVALID')
    counts={};issues=[];before,before_assessment=mapping(value['before'],'before',counts,issues);after,after_assessment=mapping(value['after'],'after',counts,issues)
    assessment=None;qualified=False
    if not issues:
        if before['id']!=after['id'] or before['model']!=after['model']:c.issue(issues,'comparison',0,'IDENTITY_MISMATCH')
        if any(before[k]!=after[k] for k in ('positive_label','negative_label')):c.issue(issues,'comparison',0,'LABEL_CONTRACT_MISMATCH')
        if after['revision']<before['revision'] or after['model_revision']<before['model_revision']:c.issue(issues,'comparison',0,'REVISION_REGRESSION')
        payload=lambda row:{key:v for key,v in row.items() if key!='revision'}
        changed=payload(before)!=payload(after)
        if changed and after['revision']<=before['revision']:c.issue(issues,'comparison',0,'CONTENT_CHANGE_REQUIRES_REVISION')
        qualified=not issues
        if qualified:
            left={r['id']:r for r in before['points']};right={r['id']:r for r in after['points']}
            assessment=dict(changed=changed,version_only=not changed and after['revision']>before['revision'],
                points_added=sorted(set(right)-set(left)),points_removed=sorted(set(left)-set(right)),
                points_changed=sorted(k for k in set(left)&set(right) if left[k]!=right[k]),model_revision_changed=before['model_revision']!=after['model_revision'])
            if changed:c.issue(issues,'comparison',0,'MAP_CHANGE_REQUIRES_REVIEW')
    return p.output(raw,'outlands-calibration-map-report-v1',counts,issues,assessment=assessment,
        map_assessments=dict(before=before_assessment,after=after_assessment),before_sha256=c.pin(before) if qualified else None,
        after_sha256=c.pin(after) if qualified else None,mapping_applied=False)

def main(argv=None):return c.cli('Validate and compare declared calibration maps; no fitting or application.',check,argv)
if __name__=='__main__':raise SystemExit(main())
