"""Reconcile selected key/payload/result claims without choosing latest or proving execution."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import cache_core as r

def record(row):
    key,out=c.record(row,{'id','operation','operation_revision','operation_sha256','key_sha256','payload_sha256','state','result_sha256'},('id','operation'),('operation_revision',))
    for field in ('operation_sha256','key_sha256','payload_sha256'):t.sha(row[field])
    t.require(row['state'] in ('pending','unknown','succeeded','failed'),'STATE_INVALID')
    if row['state'] in ('succeeded','failed'):t.sha(row['result_sha256'])
    else:t.require(row['result_sha256'] is None,'UNRESOLVED_RESULT_INVALID')
    return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','operations','records'})
    t.require(value['format']=='outlands-idempotency-ledger-v1','FORMAT_INVALID')
    counts={};issues=[];operations=r.collect(value['operations'],r.operation,'operations',counts,issues)
    records=r.collect(value['records'],record,'records',counts,issues,False)
    for position,row in records.values():
        operation=r.operation_reference(row,operations,'records',position,issues)
        if operation is not None and any(row[field]!=operation[field] for field in ('key_sha256','payload_sha256')):c.issue(issues,'records',position,'KEY_PAYLOAD_BINDING_MISMATCH')
    qualified=not issues;assessment=None
    if qualified:
        grouped=defaultdict(list);claims=defaultdict(list)
        for key,(_,operation) in sorted(operations.items()):grouped[operation['key_sha256']].append(operation)
        for key,(_,row) in sorted(records.items()):claims[row['key_sha256']].append(row)
        outcomes=[]
        for digest,ops in sorted(grouped.items()):
            selected=claims[digest];codes=[];payloads={op['payload_sha256'] for op in ops};states={row['state'] for row in selected}
            results={row['result_sha256'] for row in selected if row['state'] in ('succeeded','failed')};covered={row['operation'] for row in selected}
            if len(payloads)>1:codes.append('KEY_PAYLOAD_CONFLICT')
            if len(ops)>1:codes.append('OPERATION_KEY_ALIASES')
            if len(states)>1:codes.append('CLAIM_STATE_CONFLICT')
            if len(results)>1:codes.append('CLAIM_RESULT_CONFLICT')
            if covered!={op['id'] for op in ops}:codes.append('OPERATION_RECEIPTS_MISSING')
            if 'pending' in states:codes.append('PENDING_OUTCOME')
            if 'unknown' in states:codes.append('UNKNOWN_OUTCOME')
            unique={c.pin({k:v for k,v in row.items() if k!='id'}) for row in selected}
            terminal=not codes and len(states)==1 and next(iter(states)) in ('succeeded','failed')
            for code in codes:c.issue(issues,'keys',0,code)
            outcomes.append(dict(key_sha256=digest,operation_ids=[op['id'] for op in ops],record_ids=[row['id'] for row in selected],
                claim_records=len(selected),distinct_claims=len(unique),redundant_claim_records=len(selected)-len(unique),
                unambiguous_terminal_claim=terminal,declared_state=next(iter(states)) if terminal else 'unresolved',
                declared_result_sha256=next(iter(results)) if terminal else None,failed_criteria=codes))
        assessment=dict(key_groups=outcomes,unique_keys=len(grouped),all_terminal_claims_unambiguous=all(row['unambiguous_terminal_claim'] for row in outcomes))
    pins=dict(operations_sha256=c.cohort_pin(operations),records_sha256=c.cohort_pin(records))
    return r.output(raw,'outlands-idempotency-ledger-report-v1',counts,issues,assessment=assessment,
        ledger_reconciliation_sha256=c.pin(pins) if qualified and not issues else None,**{key:pin if qualified else None for key,pin in pins.items()})

def main(argv=None):return c.cli('Reconcile selected idempotency claims; no latest selection or execution proof.',check,argv)
if __name__=='__main__':raise SystemExit(main())
