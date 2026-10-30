"""Check declared partitions and overlaps without reading a dataset."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import dataset_common as d

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','records'})
    t.require(value['format']=='outlands-dataset-partition-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['taxonomy']);counts={};issues=[]
    records=d.records(value['records'],taxonomy['labels'],counts,issues)
    qualified=not issues;assessment=None
    if qualified:
        hashes=defaultdict(list);groups=defaultdict(list);totals=dict(train=0,validation=0,test=0)
        for key,(_,row) in sorted(records.items()):
            hashes[row['content_sha256']].append(row);groups[row['group']].append(row);totals[row['partition']]+=1
        repeated=[];overlaps=[];label_conflicts=[]
        for digest,rows in sorted(hashes.items()):
            if len(rows)>1:
                repeated.append(dict(content_sha256=digest,record_ids=[r['id'] for r in rows],partitions=sorted({r['partition'] for r in rows})))
                c.issue(issues,'records',0,'CONTENT_REPEATED')
            labels=sorted({r['label'] for r in rows})
            if len(labels)>1:
                label_conflicts.append(dict(content_sha256=digest,labels=labels,record_ids=[r['id'] for r in rows]))
                c.issue(issues,'records',0,'CONTENT_LABEL_CONFLICT')
        for group,rows in sorted(groups.items()):
            partitions=sorted({r['partition'] for r in rows})
            if len(partitions)>1:
                overlaps.append(dict(group=group,partitions=partitions,record_ids=[r['id'] for r in rows]))
                c.issue(issues,'records',0,'GROUP_CROSSES_PARTITIONS')
        assessment=dict(partition_counts=totals,repeated_content=repeated,group_overlaps=overlaps,content_label_conflicts=label_conflicts)
    return d.output(raw,'outlands-dataset-partition-report-v1',counts,issues,assessment=assessment,
        records_sha256=c.cohort_pin(records) if qualified else None,
        taxonomy_sha256=c.pin(taxonomy) if qualified else None)

def main(argv=None):return c.cli('Check explicitly declared dataset partitions; no dataset operations.',check,argv)
if __name__=='__main__':raise SystemExit(main())
