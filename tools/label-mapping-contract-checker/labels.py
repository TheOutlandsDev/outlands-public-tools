"""Check explicit taxonomy mappings without choosing destinations for real records."""
from collections import defaultdict
import toolkit as t
import decision_core as c

def mapping(row):
    key,out=c.record(row,{'id','source','targets'},('id','source'));out['targets']=c.tags(row['targets']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','before','after','mappings'});t.require(value['format']=='outlands-label-mapping-v1','FORMAT_INVALID')
    before=c.taxonomy(value['before']);after=c.taxonomy(value['after']);mappings,mc,issues=c.rows(value['mappings'],mapping,'mappings')
    if before['id']!=after['id']:c.issue(issues,'taxonomies',0,'TAXONOMY_ID_MISMATCH')
    if after['revision']<before['revision']:c.issue(issues,'taxonomies',0,'TAXONOMY_REVISION_REGRESSION')
    grouped=defaultdict(list)
    for index,row in mappings.values():
        grouped[row['source']].append(index)
        if row['source'] not in before['labels']:c.issue(issues,'mappings',index,'SOURCE_LABEL_MISSING')
        for target in row['targets']:
            if target not in after['labels']:c.issue(issues,'mappings',index,'TARGET_LABEL_MISSING')
    for source,indices in grouped.items():
        if len(indices)>1:
            for index in indices:c.issue(issues,'mappings',index,'MULTIPLE_SOURCE_MAPPINGS')
    for source in before['labels']:
        if source not in grouped:c.issue(issues,'mappings',0,'SOURCE_MAPPING_MISSING')
    changed=before['labels']!=after['labels'] or any(r['targets']!=[r['source']] for _,r in mappings.values())
    if changed and after['revision']<=before['revision']:c.issue(issues,'taxonomies',0,'MAPPING_CHANGE_NEEDS_REVISION')
    assessment=None
    if not issues:
        entries=[];incoming=defaultdict(list)
        for key,(index,row) in sorted(mappings.items()):
            kind='retired' if not row['targets'] else 'split' if len(row['targets'])>1 else 'one_to_one'
            entries.append(dict(id=key,source=row['source'],targets=row['targets'],kind=kind))
            if kind=='split':c.issue(issues,'mappings',index,'RECORD_LEVEL_SPLIT_RULE_REQUIRED')
            for target in row['targets']:incoming[target].append(row['source'])
        merges=[dict(target=target,sources=sorted(sources)) for target,sources in sorted(incoming.items()) if len(sources)>1]
        if merges:c.issue(issues,'mappings',0,'RECORD_LEVEL_MERGE_RULE_REQUIRED')
        assessment=dict(mappings=entries,merges=merges,introduced_labels=sorted(set(after['labels'])-set(incoming)),
                        record_level_rule_required=bool(merges or any(r['kind']=='split' for r in entries)))
    result=c.base(raw,'outlands-label-mapping-review-v1',dict(mappings=mc),issues)
    result.update(before_sha256=c.pin(before),after_sha256=c.pin(after),assessment=assessment,records_relabelled=False,retirement_authorized=False)
    return result

def main(argv=None):return c.cli('Review explicit label mappings; no automatic record relabeling.',check,argv)
if __name__=='__main__':raise SystemExit(main())
