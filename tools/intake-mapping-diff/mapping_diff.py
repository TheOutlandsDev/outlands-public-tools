"""Describe revisions of the existing public intake mapping; no rename inference."""
import intake
import toolkit as t
import control_core as c


def compare(raw):
    value=t.decode(raw); t.fields(value,{'format','before','after'})
    t.require(value['format']=='outlands-intake-mapping-diff-v1','FORMAT_INVALID')
    before=intake.mapping(t.encode(value['before'])); after=intake.mapping(t.encode(value['after']))
    left={f['target']:f for f in before['fields']}; right={f['target']:f for f in after['fields']}
    changes=[]
    for key in sorted(set(left)|set(right)):
        if key not in left: changes.append(dict(target=key,code='FIELD_ADDED')); continue
        if key not in right: changes.append(dict(target=key,code='FIELD_REMOVED')); continue
        for field,code in [('source','SOURCE_HEADER_CHANGED'),('type','TYPE_CHANGED'),('required','REQUIRED_CHANGED')]:
            if left[key][field]!=right[key][field]: changes.append(dict(target=key,code=code))
    for field,code in [('identity','IDENTITY_ORDER_OR_MEMBERS_CHANGED'),('unknown_columns','UNKNOWN_COLUMN_POLICY_CHANGED')]:
        if before[field]!=after[field]: changes.append(dict(target=None,code=code))
    if [f['target'] for f in before['fields']]!=[f['target'] for f in after['fields']]:
        changes.append(dict(target=None,code='FIELD_ORDER_OR_MEMBERS_CHANGED'))
    result=c.report(raw,'outlands-intake-mapping-diff-review-v1',dict(before_fields=len(left),after_fields=len(right)),[])
    result.update(status='REVIEW_REQUIRED' if changes else 'PASS',changes=changes,
                  before_mapping_sha256=t.digest(t.encode(before)),after_mapping_sha256=t.digest(t.encode(after)),
                  compatibility_verified=False,rename_inferred=False,rows_validated=False)
    return result


def main(argv=None): return c.cli('Compare supported public intake mapping declarations.',compare,argv)
if __name__=='__main__': raise SystemExit(main())
