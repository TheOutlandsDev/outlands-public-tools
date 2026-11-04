"""Fictional CLI acceptance and exact failure boundaries for Batch 95."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'tools'
ENTRY={
    'pareto-contribution-analyzer':'analyze.py',
    'pareto-cutoff-planner':'plan.py',
    'model-interface-manifest-checker':'manifest.py',
    'model-interface-revision-checker':'revisions.py',
}


def fixture(name,variant='input'):
    return json.loads((TOOLS/name/'examples'/(variant+'.json')).read_text(encoding='utf-8'))


def run(name,value):
    with tempfile.TemporaryDirectory(prefix='fictional-pareto-model-') as directory:
        path=Path(directory)/'input.json'
        path.write_text(json.dumps(value,ensure_ascii=True)+'\n',encoding='utf-8')
        result=subprocess.run([sys.executable,'-B',str(TOOLS/name/ENTRY[name]),'--input',str(path)],capture_output=True,text=True)
    if result.stderr: raise AssertionError(result.stderr)
    return result.returncode,json.loads(result.stdout)


def model_pin(row):
    normalized=dict(row,symbols=sorted(row['symbols'],key=lambda x:x['id']),inputs=sorted(row['inputs'],key=lambda x:x['id']),outputs=sorted(row['outputs'],key=lambda x:x['id']))
    raw=(json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
    return hashlib.sha256(raw).hexdigest()


class Batch95(unittest.TestCase):
    def test_fictional_examples_and_source_pins(self):
        for name in ENTRY:
            with self.subTest(name=name):
                code,report=run(name,fixture(name))
                self.assertEqual((code,report['status']),(0,'PASS'))
                result=subprocess.run([sys.executable,'-B',str(TOOLS/name/'source_check.py')],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'],'SOURCE_MATCH')
        for name in ('pareto-contribution-analyzer','pareto-cutoff-planner','model-interface-revision-checker'):
            with self.subTest(review=name):
                code,report=run(name,fixture(name,'needs-review'))
                self.assertEqual((code,report['status']),(1,'REVIEW_REQUIRED'))

    def test_pareto_tie_blocks_are_exact(self):
        code,report=run('pareto-contribution-analyzer',fixture('pareto-contribution-analyzer'))
        self.assertEqual(code,0)
        self.assertEqual(report['ranking']['total'],'12')
        self.assertEqual([(x['rank'],x['categories'],x['cumulative_share']) for x in report['ranking']['blocks']],[(1,['hvac'],'1/2'),(2,['data','game'],'1/1')])
        self.assertEqual(report['ranking']['blocks'][1]['block_total'],'6')

    def test_pareto_order_independent_and_duplicate_refused(self):
        value=fixture('pareto-contribution-analyzer')
        first=run('pareto-contribution-analyzer',value)[1]['ranking_sha256']
        value['snapshot']['rows'].reverse()
        self.assertEqual(run('pareto-contribution-analyzer',value)[1]['ranking_sha256'],first)
        value['snapshot']['rows'][0]['id']=value['snapshot']['rows'][1]['id']
        self.assertEqual(run('pareto-contribution-analyzer',value)[1]['code'],'ROW_DUPLICATE')

    def test_pareto_nonnegative_and_zero_total_review(self):
        value=fixture('pareto-contribution-analyzer')
        value['snapshot']['rows'][0]['amount']='-1'
        self.assertEqual(run('pareto-contribution-analyzer',value)[1]['code'],'DECIMAL_INVALID')
        code,report=run('pareto-contribution-analyzer',fixture('pareto-contribution-analyzer','needs-review'))
        self.assertEqual(code,1)
        self.assertTrue(all(block['cumulative_share'] is None for block in report['ranking']['blocks']))

    def test_cutoff_boundaries_and_tie_overshoot(self):
        value=fixture('pareto-cutoff-planner')
        for cutoff,selected,covered,overshoot in [('0',[], '0/1','0/1'),('0.5',['hvac'],'1/2','0/1'),('0.6',['data','game','hvac'],'1/1','2/5'),('1',['data','game','hvac'],'1/1','0/1')]:
            with self.subTest(cutoff=cutoff):
                value['cutoff']=cutoff
                code,report=run('pareto-cutoff-planner',value)
                self.assertEqual(code,0)
                self.assertEqual(report['selection']['selected_categories'],selected)
                self.assertEqual(report['selection']['covered_share'],covered)
                self.assertEqual(report['selection']['whole_block_overshoot'],overshoot)

    def test_cutoff_false_pin_and_zero_total(self):
        value=fixture('pareto-cutoff-planner')
        value['ranking_sha256']='0'*64
        self.assertEqual(run('pareto-cutoff-planner',value)[1]['code'],'RANKING_PIN_INVALID')
        code,report=run('pareto-cutoff-planner',fixture('pareto-cutoff-planner','needs-review'))
        self.assertEqual(code,1)
        self.assertIsNone(report['selection'])

    def test_manifest_symbol_and_port_boundaries(self):
        name='model-interface-manifest-checker'
        value=fixture(name)
        value['manifests'][0]['inputs'][0]['shape'][0]='missing'
        self.assertEqual(run(name,value)[1]['code'],'SYMBOL_UNKNOWN')
        value=fixture(name)
        value['manifests'][0]['symbols'].append({'id':'unused','minimum':1,'maximum':2})
        self.assertEqual(run(name,value)[1]['code'],'SYMBOL_UNUSED')
        value=fixture(name)
        value['manifests'][0]['inputs'][0]['shape'][1]=True
        self.assertEqual(run(name,value)[1]['code'],'IDENTIFIER_INVALID')
        value=fixture(name)
        value['manifests'][0]['inputs'].append(copy.deepcopy(value['manifests'][0]['inputs'][0]))
        self.assertEqual(run(name,value)[1]['code'],'PORT_DUPLICATE')

    def test_revision_additions_and_changed_shape(self):
        name='model-interface-revision-checker'
        code,report=run(name,fixture(name))
        self.assertEqual(code,0)
        self.assertEqual(report['added_ports'],{'inputs':['debug'],'outputs':['labels']})
        code,report=run(name,fixture(name,'needs-review'))
        self.assertEqual(code,1)
        self.assertEqual(report['issues'],[{'side':'inputs','port':'image','code':'SHAPE_CHANGED'}])

    def test_revision_new_required_input_and_removed_output(self):
        name='model-interface-revision-checker'
        value=fixture(name)
        value['candidate']['inputs'][1]['required']=True
        value['candidate_sha256']=model_pin(value['candidate'])
        self.assertIn('NEW_REQUIRED_INPUT',[x['code'] for x in run(name,value)[1]['issues']])
        value=fixture(name)
        value['candidate']['outputs']=[x for x in value['candidate']['outputs'] if x['id']!='scores']
        value['candidate_sha256']=model_pin(value['candidate'])
        self.assertIn('PORT_REMOVED',[x['code'] for x in run(name,value)[1]['issues']])

    def test_revision_preprocessing_and_false_pin(self):
        name='model-interface-revision-checker'
        value=fixture(name)
        value['candidate']['preprocessing_sha256']='d'*64
        value['candidate_sha256']=model_pin(value['candidate'])
        self.assertIn('PREPROCESSING_CHANGED',[x['code'] for x in run(name,value)[1]['issues']])
        value['candidate_sha256']='0'*64
        self.assertEqual(run(name,value)[1]['code'],'MANIFEST_PIN_INVALID')

    def test_duplicate_json_key_refused(self):
        name='pareto-contribution-analyzer'
        with tempfile.TemporaryDirectory(prefix='fictional-pareto-model-') as directory:
            path=Path(directory)/'duplicate.json'
            path.write_text('{"format":"x","format":"y"}',encoding='utf-8')
            result=subprocess.run([sys.executable,'-B',str(TOOLS/name/ENTRY[name]),'--input',str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['code'],'JSON_DUPLICATE_KEY')


if __name__=='__main__': unittest.main()
