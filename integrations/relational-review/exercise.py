"""Installed fictional schema-to-result declarations; never open a database."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_relational_schema_diff.schema_diff import compare
from outlands_key_reference_checker.keys import check as keys
from outlands_join_cardinality_analyzer.joins import analyze
from outlands_query_result_contract_checker.results import check as results

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')

def sample(package):
    return json.loads(files(package).joinpath('examples','input.json').read_bytes())

def main():
    result_input=sample('outlands_query_result_contract_checker');data=result_input['dataset'];schema=data['schema']
    schema_input=dict(format='outlands-relational-schema-diff-v1',before=copy.deepcopy(schema),after=schema)
    key_input=dict(format='outlands-key-reference-check-v1',dataset=data)
    join_input=dict(format='outlands-join-cardinality-v1',dataset=data,join=dict(left_table='items',right_table='entries',left_columns=['id'],right_columns=['item_id'],null_policy='never_match'))
    sr=compare(raw(schema_input));kr=keys(raw(key_input));jr=analyze(raw(join_input));rr=results(raw(result_input))
    assert sr['status']==kr['status']==jr['status']==rr['status']=='PASS'
    assert sr['before_schema_sha256']==sr['after_schema_sha256']==kr['schema_sha256']
    entries=next(row for row in kr['summary'] if row['table']=='entries')
    assert entries['foreign_keys'][0]['resolved_rows']==2 and entries['foreign_keys'][0]['skipped_null_rows']==1
    assert jr['summary']['inner_rows']==2 and jr['summary']['full_outer_rows']==4
    assert jr['summary']['key_group_shapes']['one_to_many']==1
    assert rr['summary']['returned_rows']==1 and rr['summary']['declared_complete'] is True
    expected=dict(query_sha256=hashlib.sha256(result_input['query'].encode('utf-8')).hexdigest(),dataset_sha256=hashlib.sha256(raw(data)).hexdigest(),bindings_sha256=hashlib.sha256(raw(result_input['bindings'])).hexdigest())
    assert rr['recomputed_pins']==expected
    changed=copy.deepcopy(schema_input);changed['after']['tables'][0]['columns'][1]['nullable']=True
    diff=compare(raw(changed));assert diff['status']=='REVIEW_REQUIRED' and len(diff['changes'])==1
    duplicate=copy.deepcopy(data);duplicate['tables'][0]['rows'].append(copy.deepcopy(duplicate['tables'][0]['rows'][0]))
    duplicate_keys=keys(raw(dict(format=key_input['format'],dataset=duplicate)))
    assert duplicate_keys['status']=='REVIEW_REQUIRED' and duplicate_keys['summary'] is None
    duplicate_join=copy.deepcopy(join_input);duplicate_join['dataset']=duplicate
    fanout=analyze(raw(duplicate_join));assert fanout['status']=='PASS' and fanout['summary']['inner_rows']==4 and fanout['key_constraints_evaluated'] is False
    truncated=copy.deepcopy(result_input);truncated['result']['truncated']=True
    blocked=results(raw(truncated));assert blocked['status']=='REVIEW_REQUIRED' and blocked['summary'] is None
    truncated['contract']['require_complete']=False
    allowed=results(raw(truncated));assert allowed['status']=='PASS' and allowed['summary']['declared_complete'] is False
    false_pins=copy.deepcopy(result_input)
    for side in ('contract','result'):false_pins[side]['query_sha256']='0'*64
    stale=results(raw(false_pins));assert stale['status']=='REVIEW_REQUIRED' and stale['summary'] is None and stale['recomputed_pins']['query_sha256']==expected['query_sha256']
    unrelated=copy.deepcopy(result_input);unrelated['result']['rows'][0][1]='Invented unrelated result'
    structural=results(raw(unrelated));assert structural['status']=='PASS' and structural['result_values_verified_against_query'] is False
    nulls=sample('outlands_join_cardinality_analyzer');never=analyze(raw(nulls))
    nulls['join']['null_policy']='match';matching=analyze(raw(nulls))
    assert (never['summary']['inner_rows'],never['summary']['full_outer_rows'])==(6,10)
    assert (matching['summary']['inner_rows'],matching['summary']['full_outer_rows'])==(7,9)
    for report in (sr,kr,jr,rr,diff,duplicate_keys,fanout,blocked,allowed,stale,structural,never,matching):
        assert report['sql_executed'] is False and report['target_changes_performed'] is False
        assert report['source_authority_verified'] is False and report['content_privacy_verified'] is False
    for report in (rr,allowed,structural):
        assert report['placeholder_bindings_verified'] is False and report['completeness_authority_verified'] is False
    print(json.dumps(dict(status='PASS',shared_inner_rows=2,duplicate_key_check='REVIEW_REQUIRED',duplicate_join_rows=4,schema_change='descriptive REVIEW_REQUIRED',required_truncation='summary withheld',allowed_truncation='incomplete PASS',false_pins='summary withheld',unrelated_result='structural PASS only',null_policies=dict(never_match=[6,10],match=[7,9]),sql_executed=False),sort_keys=True))

if __name__=='__main__':
    main()
