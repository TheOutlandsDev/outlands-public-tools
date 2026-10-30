"""Explicit dataset snapshots and conservative reference qualification."""
import toolkit as t
import decision_core as c

def dataset(row):
    key,out=c.record(row,{'id','revision','content_sha256','group','partition','label'},('id','group','label'),('revision',))
    t.sha(row['content_sha256']);t.require(row['partition'] in ('train','validation','test'),'PARTITION_INVALID')
    return key,out

def with_labels(parser,labels):
    def parse(row):
        key,out=parser(row)
        t.require(out['label'] in labels,'LABEL_UNKNOWN')
        return key,out
    return parse

def collect(value,parser,side,counts,issues,required=False):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def records(value,labels,counts,issues):
    return collect(value,with_labels(dataset,labels),'records',counts,issues,True)

def reference(row,records,side,position,issues):
    selected=records.get(row['record'])
    if selected is None:c.issue(issues,side,position,'RECORD_UNKNOWN');return
    target=selected[1]
    if row['record_revision']!=target['revision'] or row['record_sha256']!=c.pin(target):
        c.issue(issues,side,position,'RECORD_SNAPSHOT_MISMATCH')

def unique_slot(selected,slot,side,issues):
    slots={}
    for key,(position,row) in sorted(selected.items()):
        target=slot(row)
        if target in slots:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        else:slots[target]=row
    return slots

def output(raw,fmt,counts,issues,**values):
    report=c.base(raw,fmt,counts,issues)
    report.update(artifact_bytes_verified=False,label_truth_verified=False,
                  holdout_independence_verified=False,training_performed=False,
                  dataset_export_performed=False,**values)
    return report
