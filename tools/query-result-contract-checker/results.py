"""Check supplied result shape and actual embedded query/dataset/binding pins."""
import toolkit as t
import relational_core as c


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','contract','result','query','dataset','bindings'})
    t.require(value['format']=='outlands-query-result-contract-v1','FORMAT_INVALID')
    contract=value['contract']; pins=('query_sha256','dataset_sha256','bindings_sha256')
    t.fields(contract,{'columns','require_complete','min_rows','max_rows',*pins})
    cols=c.columns(contract['columns'])
    t.require(type(contract['require_complete']) is bool,'COMPLETENESS_POLICY_INVALID')
    minimum=t.integer(contract['min_rows'],1000); maximum=t.integer(contract['max_rows'],1000)
    t.require(minimum<=maximum,'RESULT_ROW_RANGE_INVALID')
    for field in pins: t.sha(contract[field])
    query=c.text(value['query'],4096,empty=False)
    bindings=value['bindings']; t.require(type(bindings) is dict and len(bindings)<=32,'BINDING_LIMIT')
    for key,item in bindings.items():
        t.identifier(key)
        if item is None or type(item) is bool: continue
        if type(item) is int: t.integer(item,10**12,-10**12)
        else: c.text(item)
    schema,tables,counts,issues=c.dataset(value['dataset'])
    issues=[dict(row,table='dataset:'+row['table']) for row in issues]
    result=value['result']; t.fields(result,{'columns','rows','truncated',*pins})
    selected=c.names(result['columns'],16); t.require(type(result['truncated']) is bool,'TRUNCATION_FLAG_INVALID')
    actual=dict(query_sha256=t.digest(query.encode('utf-8')),dataset_sha256=t.digest(t.encode(value['dataset'])),
                bindings_sha256=t.digest(t.encode(bindings)))
    for field in pins:
        t.sha(result[field])
        if contract[field]!=actual[field]: c.issue(issues,'contract',0,field.upper()+'_MISMATCH')
        if result[field]!=actual[field]: c.issue(issues,'result',0,field.upper()+'_MISMATCH')
    if selected!=[col['name'] for col in cols]: c.issue(issues,'result',0,'RESULT_COLUMN_ORDER_OR_NAMES_MISMATCH')
    rows,rc,other=c.rows(result['rows'],cols,'result'); issues+=other
    counts=dict(dataset=counts,result=rc)
    if not minimum<=len(result['rows'])<=maximum: c.issue(issues,'result',0,'RESULT_ROW_RANGE_MISMATCH')
    if contract['require_complete'] and result['truncated']: c.issue(issues,'result',0,'TRUNCATED_RESULT')
    report=c.base(raw,'outlands-query-result-contract-review-v1',counts,issues)
    report.update(summary=dict(returned_rows=len(rows),declared_complete=not result['truncated']) if not issues else None,
                  recomputed_pins=actual,completeness_authority_verified=False,result_values_verified_against_query=False,
                  placeholder_bindings_verified=False)
    return report


def main(argv=None): return c.cli('Check supplied query-result types, pins and declared truncation without executing SQL.',check,argv)
if __name__=='__main__': raise SystemExit(main())
