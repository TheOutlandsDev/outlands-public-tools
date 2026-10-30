import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import impacts as app

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        r=self.run_value(value);self.assertEqual(r['status'],'REVIEW_REQUIRED');self.assertTrue(r['issues']);return r
    def withheld(self,value=None):
        r=self.review(value);self.assertIsNone(r['assessment'])
        for key in ['review_scope_sha256', 'nodes_sha256', 'dependencies_sha256', 'changes_sha256']:self.assertIsNone(r[key])
        return r
    def test_positive_and_authority_boundaries(self):
        r=self.run_value();self.assertEqual(r['status'],'PASS')
        for key in ('artifact_bytes_verified','reviewer_identity_verified','approval_authority_verified','records_changed','execution_performed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(r[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_row_order_preserves_full_scope_pins(self):
        before=self.run_value()
        for key in ['nodes', 'dependencies', 'changes']:self.value[key].reverse()
        after=self.run_value()
        for key in ['review_scope_sha256', 'nodes_sha256', 'dependencies_sha256', 'changes_sha256']:self.assertEqual(before[key],after[key])
    def test_identical_identity_snapshots_count_once(self):
        for key in ['nodes', 'dependencies', 'changes']:
            if not self.value[key]:continue
            value=copy.deepcopy(self.value);value[key].append(copy.deepcopy(value[key][0]));r=self.run_value(value)
            self.assertEqual(r['status'],'PASS');counts=r['counts'][key];self.assertEqual(counts['duplicate_rows'],1)
            self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_bad_rows_withhold_and_omit_supplied_values(self):
        for key in ['nodes', 'dependencies', 'changes']:
            value=copy.deepcopy(self.value);value[key].append({'id':'SYNTHETIC_SENTINEL'});r=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(r))
    def test_list_bounds_and_nonlist_are_fixed_refusals(self):
        for key in ['nodes', 'dependencies', 'changes']:
            for rows in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);value[key]=rows
                with self.assertRaises(t.Rejected):self.run_value(value)

    def test_conflicting_identity_groups_exclude_every_member(self):
        for side in ['nodes', 'dependencies', 'changes']:
            if not self.value[side]:continue
            value=copy.deepcopy(self.value);row=copy.deepcopy(value[side][0])
            field=next(k for k in row if k!='id' and isinstance(row[k],(str,int)) and row[k] is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            value[side].extend([row,copy.deepcopy(value[side][0])]);r=self.withheld(value)
            self.assertEqual(r['counts'][side]['conflict_rows'],3)
    def test_input_pin_is_raw_and_reports_are_deterministic(self):
        raw=encode(self.value);r=app.check(raw);self.assertEqual(r['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(r,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(r['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(r['review_scope_sha256'],app.check(spaced)['review_scope_sha256'])
    def test_required_cohort_is_not_vacuously_valid(self):
        self.value[['nodes', 'dependencies', 'changes'][0]]=[];self.withheld()
    def test_unknown_fields_and_nonobjects_are_rejected_rows(self):
        for side in ['nodes', 'dependencies', 'changes']:
            value=copy.deepcopy(self.value);value[side].append(None);self.withheld(value)
            if value[side][:-1]:
                value=copy.deepcopy(self.value);value[side][0]['extra']=0;self.withheld(value)

    def edge(self,up,down,id='extra-edge'):
        nodes={row['id']:row for row in self.value['nodes']};return dict(id=id,upstream=up,upstream_revision=nodes[up]['revision'],upstream_sha256=pin(nodes[up]),downstream=down,downstream_revision=nodes[down]['revision'],downstream_sha256=pin(nodes[down]))
    def test_known_transitive_closure_and_unaffected_node(self):
        r=self.run_value();self.assertEqual(r['assessment']['recheck_nodes'],[dict(id='hvac-review-summary',caused_by=['hvac-service-spec'],directly_changed=False),dict(id='hvac-service-plan',caused_by=['hvac-service-spec'],directly_changed=False),dict(id='hvac-service-spec',caused_by=['hvac-service-spec'],directly_changed=True)])
        self.assertEqual(r['assessment']['unaffected_node_ids'],['hvac-unrelated-demo']);self.assertFalse(r['assessment']['dependency_discovery_complete'])
    def test_reverse_direction_is_not_affected(self):
        node=self.value['nodes'][2];self.value['changes'][0].update(node=node['id'],node_revision=node['revision'],node_sha256=pin(node));r=self.run_value();self.assertEqual([row['id'] for row in r['assessment']['recheck_nodes']],['hvac-review-summary'])
    def test_diamond_and_multiple_roots_preserve_all_causes(self):
        a,b,c,d=[row['id'] for row in self.value['nodes']];self.value['dependencies'].extend([self.edge(a,d),self.edge(d,c,'diamond')]);node=self.value['nodes'][1];self.value['changes'].append(dict(id='change-two',node=b,node_revision=node['revision'],node_sha256=pin(node)))
        r=self.run_value();out=next(row for row in r['assessment']['recheck_nodes'] if row['id']==c);self.assertEqual(out['caused_by'],sorted([a,b]))
    def test_cycle_or_self_loop_withholds_entire_plan(self):
        for up,down in [('hvac-review-summary','hvac-service-spec'),('hvac-unrelated-demo','hvac-unrelated-demo')]:
            value=copy.deepcopy(self.value);value['dependencies'].append(self.edge(up,down));self.withheld(value)
    def test_cycle_in_disconnected_component_is_not_ignored(self):
        self.value['dependencies'].append(self.edge('hvac-unrelated-demo','hvac-unrelated-demo'));self.withheld()
    def test_stale_edge_and_change_pins_withhold(self):
        for side,field in [('dependencies','downstream_sha256'),('changes','node_sha256')]:
            value=copy.deepcopy(self.value);value[side][0][field]='0'*64;self.withheld(value)
    def test_unknown_node_is_not_discovered(self):
        self.value['changes'][0]['node']='missing';self.withheld()
    def test_aliased_dependency_or_change_is_ambiguous(self):
        for side in ('dependencies','changes'):
            value=copy.deepcopy(self.value);value[side].append(dict(value[side][0],id='alias'));self.withheld(value)
    def test_no_dependencies_only_rechecks_explicit_root(self):
        self.value['dependencies']=[];r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['assessment']['recheck_nodes']),1)
    def test_empty_changes_never_issues_a_noop_qualification(self):
        self.value['changes']=[];self.withheld()
    def test_long_graph_is_iterative_not_recursion_limited(self):
        self.value['nodes']=[dict(id='node-'+str(n),revision=1,artifact_sha256=pin(n)) for n in range(700)];self.value['dependencies']=[self.edge('node-'+str(n),'node-'+str(n+1),'edge-'+str(n)) for n in range(699)]
        self.value['changes']=[dict(id='change-root',node='node-0',node_revision=1,node_sha256=pin(self.value['nodes'][0]))];r=self.run_value();self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['assessment']['recheck_nodes']),700)
    def test_dense_root_cause_expansion_is_a_fixed_refusal(self):
        self.value['nodes']=[dict(id='node-'+str(n),revision=1,artifact_sha256=pin(n)) for n in range(400)];self.value['dependencies']=[self.edge('node-'+str(n),'node-'+str(n+1),'edge-'+str(n)) for n in range(399)]
        self.value['changes']=[dict(id='change-'+str(n),node=row['id'],node_revision=1,node_sha256=pin(row)) for n,row in enumerate(self.value['nodes'])]
        with self.assertRaisesRegex(t.Rejected,'^IMPACT_CAUSE_LIMIT$'):self.run_value()
    def test_disconnected_roots_are_both_retained(self):
        node=self.value['nodes'][3];self.value['changes'].append(dict(id='change-other',node=node['id'],node_revision=1,node_sha256=pin(node)));r=self.run_value();self.assertEqual(r['assessment']['unaffected_node_ids'],[]);self.assertEqual(len(r['assessment']['changed_node_ids']),2)
