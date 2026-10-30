"""Compare selected decimal readings with an explicitly pinned rule revision."""
import toolkit as t
import quality_core as c

def measurement(row):
    key,out=c.record(row,{'id','specimen_id','check_id','rule_id','rule_revision','unit','value'},('id','specimen_id','check_id','rule_id','unit'),(('rule_revision',1,10**6),))
    _,out['value']=c.decimal(row['value']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','rules','measurements'})
    t.require(value['format']=='outlands-measurement-contract-v1','FORMAT_INVALID')
    rules,rc,issues=c.rows(value['rules'],c.rule,'rules');rules_valid=not issues
    measurements,mc,other=c.rows(value['measurements'],measurement,'measurements');issues+=other
    if not rules:c.issue(issues,'rules',0,'EMPTY_RULE_COHORT');rules_valid=False
    if not measurements:c.issue(issues,'measurements',0,'EMPTY_MEASUREMENT_COHORT')
    c.unique_pairs(measurements,('specimen_id','check_id'),'measurements',issues,'MULTIPLE_MEASUREMENTS_FOR_CHECK')
    for index,row in measurements.values():
        if row['rule_id'] not in rules:c.issue(issues,'measurements',index,'RULE_MISSING')
        else:
            rule=rules[row['rule_id']][1]
            if row['rule_revision']!=rule['revision']:c.issue(issues,'measurements',index,'RULE_REVISION_MISMATCH')
            if row['unit']!=rule['unit']:c.issue(issues,'measurements',index,'UNIT_MISMATCH')
    assessments=None
    if not issues:
        assessments=[]
        for key,(index,row) in sorted(measurements.items()):
            rule=rules[row['rule_id']][1];reading=c.decimal(row['value'])[0];low=c.decimal(rule['minimum'])[0];high=c.decimal(rule['maximum'])[0]
            reasons=[]
            if reading<low or (reading==low and not rule['minimum_inclusive']):reasons.append('BELOW_MINIMUM')
            if reading>high or (reading==high and not rule['maximum_inclusive']):reasons.append('ABOVE_MAXIMUM')
            if reasons:c.issue(issues,'measurements',index,'READING_OUTSIDE_LIMITS')
            assessments.append(dict(row,within_declared_limits=not reasons,reasons=reasons))
    result=c.base(raw,'outlands-measurement-review-v1',dict(rules=rc,measurements=mc),issues)
    result.update(assessments=assessments,rule_contract_sha256=c.pin(rules) if rules_valid else None,
                  equipment_suitability_verified=False,measurement_accuracy_verified=False,settings_changed=False)
    return result

def main(argv=None):return c.cli('Check supplied decimal readings; no equipment approval or device access.',check,argv)
if __name__=='__main__':raise SystemExit(main())
