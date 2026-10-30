"""Reconcile pinned annotation selections, category mappings and approval declarations."""
import toolkit as t
import decision_core as c
import visual_core as v

def category(row):
    key,out=c.record(row,{'id','label','index'},('id','label'));t.integer(row['index'],255);return key,out

def approval(row):
    key,out=c.record(row,{'id','annotation','annotation_revision','annotation_sha256','decision'},('id','annotation'),('annotation_revision',))
    t.sha(row['annotation_sha256']);t.require(row['decision'] in ('approve','reject'),'DECISION_INVALID');return key,out

def handoff(value,labels):
    _,out=c.record(value,{'id','revision','images_sha256','annotations_sha256','taxonomy_sha256','categories_sha256',
        'selected_annotations','expected_images','expected_annotations','expected_label_counts'},('id',),('revision',))
    for key in ('images_sha256','annotations_sha256','taxonomy_sha256','categories_sha256'):t.sha(value[key])
    selected=value['selected_annotations'];t.require(type(selected) is list and 1<=len(selected)<=1000,'SELECTION_LIMIT')
    for key in selected:t.identifier(key)
    t.require(len(set(selected))==len(selected),'SELECTION_DUPLICATE');out['selected_annotations']=sorted(selected)
    for key in ('expected_images','expected_annotations'):t.integer(value[key],1000,1)
    t.fields(value['expected_label_counts'],labels)
    for n in value['expected_label_counts'].values():t.integer(n,1000)
    return out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','images','annotations','categories','approvals','handoff'})
    t.require(value['format']=='outlands-annotation-export-handoff-v1','FORMAT_INVALID')
    counts={};issues=[];taxonomy,images,annotations=v.scope(value,counts,issues)
    categories=v.collect(value['categories'],category,'categories',counts,issues)
    approvals=v.collect(value['approvals'],approval,'approvals',counts,issues,False)
    plan=handoff(value['handoff'],taxonomy['labels']);labels={};indexes={};reviews={}
    for position,row in categories.values():
        if row['label'] not in taxonomy['labels']:c.issue(issues,'categories',position,'LABEL_UNKNOWN')
        if row['label'] in labels or row['index'] in indexes:c.issue(issues,'categories',position,'CATEGORY_MAPPING_AMBIGUOUS')
        labels[row['label']]=row['index'];indexes[row['index']]=row['label']
    if set(labels)!=set(taxonomy['labels']):c.issue(issues,'categories',0,'CATEGORY_COVERAGE_MISMATCH')
    for position,row in approvals.values():
        target=annotations.get(row['annotation'])
        if target is None:c.issue(issues,'approvals',position,'ANNOTATION_UNKNOWN')
        elif row['annotation_revision']!=target[1]['revision'] or row['annotation_sha256']!=c.pin(target[1]):c.issue(issues,'approvals',position,'ANNOTATION_SNAPSHOT_MISMATCH')
        if row['annotation'] in reviews:c.issue(issues,'approvals',position,'APPROVAL_AMBIGUOUS')
        reviews[row['annotation']]=row
    for key in plan['selected_annotations']:
        if key not in annotations:c.issue(issues,'handoff',0,'ANNOTATION_UNKNOWN')
    pins=dict(images_sha256=c.cohort_pin(images),annotations_sha256=c.cohort_pin(annotations),taxonomy_sha256=c.pin(taxonomy),categories_sha256=c.cohort_pin(categories))
    for key,pin in pins.items():
        if plan[key]!=pin:c.issue(issues,'handoff',0,'SCOPE_PIN_MISMATCH')
    qualified=not issues;assessment=None;selection_pin=None
    if qualified:
        selected=[annotations[key][1] for key in plan['selected_annotations']];used=sorted({r['image'] for r in selected})
        actual_labels={label:sum(r['label']==label for r in selected) for label in taxonomy['labels']};failures=[]
        if len(used)!=plan['expected_images']:failures.append('IMAGE_COUNT_MISMATCH')
        if len(selected)!=plan['expected_annotations']:failures.append('ANNOTATION_COUNT_MISMATCH')
        if actual_labels!=plan['expected_label_counts']:failures.append('LABEL_COUNTS_MISMATCH')
        missing=[r['id'] for r in selected if r['id'] not in reviews]
        rejected=[r['id'] for r in selected if r['id'] in reviews and reviews[r['id']]['decision']!='approve']
        if missing:failures.append('APPROVAL_MISSING')
        if rejected:failures.append('APPROVAL_REJECTED')
        for code in failures:c.issue(issues,'handoff',0,code)
        assessment=dict(selected_images=used,images=len(used),annotations=len(selected),label_counts=actual_labels,
            label_to_index=labels,missing_approvals=missing,rejected_approvals=rejected,failed_criteria=failures,
            eligible_for_manual_export_review=not failures)
        if not failures:selection_pin=c.pin(selected)
    return v.output(raw,'outlands-annotation-export-handoff-report-v1',counts,issues,assessment=assessment,
        **{key:pin if qualified else None for key,pin in pins.items()},handoff_sha256=c.pin(plan) if qualified else None,
        selected_annotations_sha256=selection_pin,geometry_verified=False)

def main(argv=None):return c.cli('Review an explicit annotation handoff; never export images or labels.',check,argv)
if __name__=='__main__':raise SystemExit(main())
