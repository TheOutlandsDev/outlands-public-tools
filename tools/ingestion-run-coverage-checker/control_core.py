"""Complete row accounting and explicitly selected batch/receipt snapshots."""
from collections import defaultdict
import toolkit as t

COUNT_FIELDS={'input_rows','accepted_records','duplicate_rows','rejected_rows','conflict_rows'}
BATCH_FIELDS={'id','sequence','source_sha256','mapping_sha256','preview_sha256','counts'}


def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list); issues=[]; rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row); groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1; issues.append(dict(side=side,row=index,code=str(error)))
    accepted={}; duplicate=conflict=0
    for key,entries in groups.items():
        if len({t.encode(row) for _,row in entries})!=1:
            conflict+=len(entries)
            issues.extend(dict(side=side,row=index,code='IDENTITY_CONFLICT') for index,_ in entries)
        else:
            accepted[key]=entries[0]; duplicate+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicate,
                conflict_rows=conflict,rejected_rows=rejected)
    t.require(len(value)==sum(counts[k] for k in COUNT_FIELDS-{'input_rows'}),'ACCOUNTING_FAILED')
    return accepted,counts,issues


def accounting(value):
    t.fields(value,COUNT_FIELDS)
    for count in value.values(): t.integer(count,1000)
    t.require(value['input_rows']==sum(value[k] for k in COUNT_FIELDS-{'input_rows'}),'DECLARED_ACCOUNTING_MISMATCH')
    return dict(value)


def batch(row):
    t.fields(row,BATCH_FIELDS); t.identifier(row['id']); t.integer(row['sequence'],10**9,1)
    for key in ('source_sha256','mapping_sha256','preview_sha256'): t.sha(row[key])
    accounting(row['counts'])
    return row['id'],dict(row)


def receipt(row):
    t.fields(row,{'receipt_id','stream','batch','status','receipt_sha256'})
    t.identifier(row['receipt_id']); t.identifier(row['stream']); t.sha(row['receipt_sha256'])
    batch(row['batch'])
    t.require(row['status'] in ('committed','failed','uncertain'),'RECEIPT_STATUS_INVALID')
    return row['batch']['id'],dict(row)


def clean(row):
    counts=row['counts']
    return counts['input_rows']>0 and counts['accepted_records']>0 and counts['rejected_rows']==counts['conflict_rows']==0


def problem(issues,side,index,code): issues.append(dict(side=side,row=index,code=code))


def prepare(value):
    t.identifier(value['stream'])
    expected,ec,issues=rows(value['expected'],batch,'expected')
    receipts,rc,other=rows(value['receipts'],receipt,'receipts'); issues+=other
    sequences=defaultdict(list); receipt_ids=defaultdict(list); content=defaultdict(list)
    for key,(index,row) in expected.items():
        sequences[row['sequence']].append(('expected',index,key))
        content[tuple(row[f] for f in ('source_sha256','mapping_sha256','preview_sha256'))].append(('expected',index,key))
        if not clean(row): problem(issues,'expected',index,'BATCH_COUNTS_REQUIRE_REVIEW')
    for key,(index,row) in receipts.items():
        sequences[row['batch']['sequence']].append(('receipts',index,key))
        content[tuple(row['batch'][f] for f in ('source_sha256','mapping_sha256','preview_sha256'))].append(('receipts',index,key))
        receipt_ids[row['receipt_id']].append(index)
        if row['stream']!=value['stream']: problem(issues,'receipts',index,'STREAM_MISMATCH')
    for entries in sequences.values():
        if len({key for _,_,key in entries})>1:
            for side,index,_ in entries: problem(issues,side,index,'SEQUENCE_ALIAS')
    for indices in receipt_ids.values():
        if len(indices)>1:
            for index in indices: problem(issues,'receipts',index,'RECEIPT_ID_ALIAS')
    for entries in content.values():
        if len({key for _,_,key in entries})>1:
            for side,index,_ in entries: problem(issues,side,index,'CONTENT_ID_ALIAS')
    return expected,receipts,dict(expected=ec,receipts=rc),issues


def equal_batch(first,second): return t.encode(first)==t.encode(second)


def reconcile(expected,receipts,issues,allow_history=False):
    matched=[]; missing=[]; orphan=[]
    for key,(index,row) in sorted(expected.items()):
        if key not in receipts:
            missing.append(key); problem(issues,'expected',index,'RECEIPT_MISSING'); continue
        ri,receipt_row=receipts[key]
        if not equal_batch(row,receipt_row['batch']): problem(issues,'receipts',ri,'BATCH_METADATA_MISMATCH'); continue
        if receipt_row['status']!='committed':
            problem(issues,'receipts',ri,'OUTCOME_'+receipt_row['status'].upper()); continue
        if not clean(receipt_row['batch']): problem(issues,'receipts',ri,'RECEIPT_COUNTS_REQUIRE_REVIEW'); continue
        matched.append(row)
    if not allow_history:
        for key,(index,_) in sorted(receipts.items()):
            if key not in expected:
                orphan.append(key); problem(issues,'receipts',index,'UNEXPECTED_RECEIPT')
    return matched,len(missing),len(orphan)


def report(raw,fmt,counts,issues):
    # Drop only repeated diagnostics, never any source row.
    issues=[dict(side=side,row=index,code=code) for side,index,code in sorted({(r['side'],r['row'],r['code']) for r in issues})]
    return dict(format=fmt,status='REVIEW_REQUIRED' if issues else 'PASS',input_sha256=t.digest(raw),
                counts=counts,issues=issues,row_counts_recomputed=False,receipt_authority_verified=False,
                exactly_once_verified=False,target_changes_performed=False)


def cli(description,operation,argv=None):
    p=t.Parser(description=description); p.add_argument('--input',required=True); p.add_argument('--out')
    return t.run(p,lambda a:operation(t.read(a.input)),argv)
