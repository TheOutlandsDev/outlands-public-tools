"""Installed fictional configuration review; no values, targets or adapter reads."""
import copy
import hashlib
import json
from importlib.resources import files
from outlands_configuration_overlay_planner.overlays import check as overlays
from outlands_configuration_contract_diff.contracts import check as contracts
from outlands_compatibility_matrix_checker.matrix import check as matrix
from outlands_configuration_migration_path_checker.migrations import check as migrations

OPS=(overlays,contracts,matrix,migrations)
PACKAGES=('outlands_configuration_overlay_planner','outlands_configuration_contract_diff',
          'outlands_compatibility_matrix_checker','outlands_configuration_migration_path_checker')

def raw(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(raw(value)).hexdigest()
def run(index,value):return OPS[index](raw(value))
def codes(report):return {row['code'] for row in report['issues']}
def sample(index,name='input.json'):
    return json.loads(files(PACKAGES[index]).joinpath('examples',name).read_bytes())

def main():
    values=[sample(i) for i in range(4)];reports=[run(i,v) for i,v in enumerate(values)];checked=list(reports)
    overlay,diff,pairs,path=reports
    assert all(r['status']=='PASS' and r['qualified_scope_sha256'] for r in reports)
    assert overlay['contract_sha256']==diff['baseline_sha256']==values[3]['source']['sha256']
    assert diff['candidate_sha256']==values[3]['target']['sha256']
    assert all(row['contract_sha256']==diff['candidate_sha256'] for row in values[2]['components'])
    assert len(overlay['assessment']['effective_fields'])==3
    assert diff['assessment']['header_changed'] is True and diff['assessment']['all_field_metadata_equal'] is True
    assert pairs['assessment']['all_requested_pairs_declared_supported'] is True
    assert path['assessment']['target_reached'] is True and path['assessment']['checks_executed'] is False
    # Identical normalized declarations count once; cohort pins are unchanged.
    fields=(('layers','changes'),(),('components','rules','requirements'),('contracts','steps'))
    for i,value in enumerate(values):
        duplicate=copy.deepcopy(value)
        for field in fields[i]:duplicate[field].append(copy.deepcopy(duplicate[field][0]))
        if i==1:
            for side in ('baseline','candidate'):duplicate[side]['fields'].append(copy.deepcopy(duplicate[side]['fields'][0]))
        report=run(i,duplicate);checked.append(report)
        assert report['status']=='PASS' and report['qualified_scope_sha256']==reports[i]['qualified_scope_sha256']
        assert any(count['duplicate_rows']==1 for count in report['counts'].values())
    review=[run(i,sample(i,'needs-review.json')) for i in range(4)];checked.extend(review)
    assert all(r['status']=='REVIEW_REQUIRED' and r['assessment'] is not None for r in review)
    assert review[0]['effective_configuration_sha256'] is None
    assert review[1]['assessment']['all_field_metadata_equal'] is False
    assert review[2]['assessment']['requirements'][0]['state']=='unsupported'
    assert review[3]['assessment']['target_reached'] is False
    # A supplied default does not create a missing required key.
    absent=copy.deepcopy(values[0]);absent['changes']=[r for r in absent['changes'] if r['key']!='queue_limit']
    report=run(0,absent);checked.append(report)
    assert 'REQUIRED_KEY_MISSING' in codes(report) and report['assessment']['defaults_inserted'] is False
    assert report['assessment']['effective_fields'] is None
    # Delete then explicitly restore a required key in a later layer.
    restored=copy.deepcopy(values[0]);replacement=next(r for r in restored['changes'] if r['id']=='override-limit');saved=copy.deepcopy(replacement)
    replacement.update(action='delete',value_type=None,value_sha256=None,allow_override=False)
    layer=dict(restored['layers'][-1],id='restore-layer',ordinal=3);restored['layers'].append(layer)
    saved.update(id='restore-limit',layer=layer['id'],layer_sha256=pin(layer),allow_override=False);restored['changes'].append(saved)
    report=run(0,restored);checked.append(report)
    assert report['status']=='PASS' and report['effective_configuration_sha256']==overlay['effective_configuration_sha256']
    assert report['changes_sha256']!=overlay['changes_sha256']
    assert next(r for r in report['assessment']['effective_fields'] if r['key']=='queue_limit')['source_layer']=='restore-layer'
    stale=copy.deepcopy(values[0]);stale['layers'][0]['contract_sha256']='0'*64
    report=run(0,stale);checked.append(report)
    assert report['assessment'] is None and report['contract_sha256'] is None and 'CONTRACT_PIN_MISMATCH' in codes(report)
    conflict=copy.deepcopy(values[1]);conflict['candidate']=copy.deepcopy(conflict['baseline']);conflict['candidate']['fields'][0]['required']=False
    report=run(1,conflict);checked.append(report)
    assert 'CONTRACT_IDENTITY_CONFLICT' in codes(report) and report['assessment'] is None and report['baseline_sha256'] is None
    missing=copy.deepcopy(values[2]);missing['rules']=[]
    report=run(2,missing);checked.append(report)
    assert report['assessment']['requirements'][0]['state']=='unlisted'
    extra=copy.deepcopy(values[2]);extra['components'].append(dict(extra['components'][0],id='optional-console'))
    report=run(2,extra);checked.append(report)
    assert report['status']=='PASS' and report['assessment']['unrequested_pairs_checked'] is False
    reversed_pairs=copy.deepcopy(values[2])
    for side in ('rules','requirements'):
        reversed_row=copy.deepcopy(reversed_pairs[side][0])
        for suffix in ('','_revision','_sha256'):reversed_row['left'+suffix],reversed_row['right'+suffix]=reversed_row['right'+suffix],reversed_row['left'+suffix]
        reversed_pairs[side].append(reversed_row)
    report=run(2,reversed_pairs);checked.append(report)
    assert report['status']=='PASS' and report['qualified_scope_sha256']==pairs['qualified_scope_sha256']
    assert report['counts']['rules']['duplicate_rows']==report['counts']['requirements']['duplicate_rows']==1
    version=copy.deepcopy(values[2]);version['components'][0]['version']='demo-v3'
    report=run(2,version);checked.append(report)
    assert 'SNAPSHOT_MISMATCH' in codes(report) and report['assessment'] is None
    short=copy.deepcopy(values[3]);short['steps']=[]
    report=run(3,short);checked.append(report)
    assert report['assessment']['target_reached'] is False and 'PATH_TARGET_NOT_REACHED' in codes(report)
    no_op=copy.deepcopy(short);no_op['target']=copy.deepcopy(no_op['source'])
    report=run(3,no_op);checked.append(report);assert report['status']=='PASS' and report['assessment']['target_reached'] is True
    gap=copy.deepcopy(values[3]);gap['steps'][0]['ordinal']=2
    report=run(3,gap);checked.append(report);assert 'STEP_ORDINAL_GAP' in codes(report) and report['assessment'] is None
    cycle=copy.deepcopy(values[3]);back=copy.deepcopy(cycle['steps'][0]);back.update(id='return-step',ordinal=2)
    for suffix in ('','_revision','_sha256'):back['from_contract'+suffix],back['to_contract'+suffix]=back['to_contract'+suffix],back['from_contract'+suffix]
    cycle['steps'].append(back);report=run(3,cycle);checked.append(report)
    assert 'PATH_CYCLE' in codes(report) and report['assessment'] is None
    adapter=copy.deepcopy(values[3]);adapter['steps'][0]['adapter_sha256']='0'*64
    report=run(3,adapter);checked.append(report)
    assert report['status']=='PASS' and report['adapter_bytes_verified'] is False and report['assessment']['adapters_opened'] is False
    for report in checked:
        for field in ('raw_setting_values_emitted','settings_values_validated','runtime_compatibility_verified','adapter_bytes_verified','migration_executed','configuration_changed','installation_performed','execution_performed','target_changes_performed','execution_authorized','declarations_independently_verified'):
            assert report[field] is False
        if report['status']=='REVIEW_REQUIRED':assert report['qualified_scope_sha256'] is None
    print(json.dumps(dict(status='PASS',effective_fields=3,shared_contract_pins='matched',duplicates='counted once',header_change='field metadata equal',default='not inserted',delete_restore='explicit; same final metadata pin',stale_references='assessment withheld',identity_conflict='assessment withheld',pair_states=['supported','unsupported','unlisted'],symmetric_pairs='normalized',unrequested_pairs='not assessed',migration=['short reviewed','no-op passed','gap/cycle withheld'],adapter_bytes_verified=False,settings_values_validated=False,migration_executed=False,configuration_changed=False),sort_keys=True))

if __name__=='__main__':main()
