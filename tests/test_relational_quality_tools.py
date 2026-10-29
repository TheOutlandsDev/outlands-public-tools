"""Actual CLI interoperability on fictional intake records; no SQL or private source."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'relational-schema-diff':'schema_diff.py','key-reference-checker':'keys.py',
       'join-cardinality-analyzer':'joins.py','query-result-contract-checker':'results.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def col(name,type='text',nullable=False): return dict(name=name,type=type,nullable=nullable)

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-relational-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        p=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(p.stderr,b''); return p.returncode,json.loads(p.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_source_copies(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_refusal(self):
        for name in TOOLS:
            out=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',out))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertFalse(out.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',))
            self.assertEqual(code,2); self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1); self.assertEqual(result['status'],'REVIEW_REQUIRED')
            if name=='relational-schema-diff': self.assertEqual(len(result['changes']),1)
            else: self.assertIsNone(result['summary'])

    def test_raw_input_pins_and_no_mutation(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes()
            _,result=self.cli(name); self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_actual_public_intake_and_four_tool_cohort(self):
        mapping=dict(format='outlands-table-map-v1',identity=['id'],unknown_columns='reject',fields=[
            dict(source='Record',target='id',type='text',required=True),dict(source='Units',target='units',type='integer',required=True)])
        source=self.root/'invented.csv'; source.write_bytes(b'Record,Units\nalpha,3\nbeta,4\n')
        map_path=self.root/'mapping.json'; map_path.write_bytes(encode(mapping))
        code,intake=self.invoke(ROOT/'tools/workbook-intake-checker/intake.py',['--input',source,'--mapping',map_path,'--format','csv'])
        self.assertEqual(code,0); self.assertEqual(intake['counts']['accepted_records'],2)
        items=[[row['record']['id'],row['record']['units']] for row in intake['accepted']]
        schema=dict(tables=[dict(name='items',columns=[col('id'),col('units','integer')],primary_key=['id'],foreign_keys=[]),
            dict(name='links',columns=[col('entry_id','integer'),col('item_id')],primary_key=['entry_id'],foreign_keys=[
                dict(name='item_ref',columns=['item_id'],table='items',references=['id'],null_policy='reject')])])
        data=dict(schema=schema,tables=[dict(name='items',rows=items),dict(name='links',rows=[[1,'alpha'],[2,'alpha'],[3,'beta']])])
        query='SELECT id, units FROM items WHERE id = :selected'; bindings=dict(selected='alpha')
        pins=dict(query_sha256=sha(query.encode()),dataset_sha256=sha(encode(data)),bindings_sha256=sha(encode(bindings)))
        # Python fixture selection only; no SQL engine or query execution.
        selected=[row for row in items if row[0]=='alpha']
        inputs={
          'relational-schema-diff':dict(format='outlands-relational-schema-diff-v1',before=schema,after=schema),
          'key-reference-checker':dict(format='outlands-key-reference-check-v1',dataset=data),
          'join-cardinality-analyzer':dict(format='outlands-join-cardinality-v1',dataset=data,
              join=dict(left_table='items',right_table='links',left_columns=['id'],right_columns=['item_id'],null_policy='never_match')),
          'query-result-contract-checker':dict(format='outlands-query-result-contract-v1',query=query,dataset=data,bindings=bindings,
              contract=dict(columns=schema['tables'][0]['columns'],require_complete=True,min_rows=1,max_rows=2,**pins),
              result=dict(columns=['id','units'],rows=selected,truncated=False,**pins))}
        outputs={}
        for name,value in inputs.items():
            file=self.root/(name+'.json'); file.write_bytes(encode(value)); code,result=self.cli(name,file=file)
            self.assertEqual(code,0); self.assertFalse(result['sql_executed']); outputs[name]=result
        self.assertEqual(outputs['relational-schema-diff']['changes'],[])
        linked=next(row for row in outputs['key-reference-checker']['summary'] if row['table']=='links')
        self.assertEqual(linked['foreign_keys'][0]['resolved_rows'],3)
        self.assertEqual(outputs['join-cardinality-analyzer']['summary']['inner_rows'],3)
        self.assertEqual(outputs['join-cardinality-analyzer']['summary']['key_group_shapes']['one_to_many'],1)
        self.assertEqual(outputs['query-result-contract-checker']['summary']['returned_rows'],1)
        self.assertEqual(outputs['query-result-contract-checker']['recomputed_pins'],pins)
        self.assertFalse(outputs['query-result-contract-checker']['result_values_verified_against_query'])

    def test_private_values_omitted(self):
        for name in ('key-reference-checker','join-cardinality-analyzer','query-result-contract-checker'):
            _,result=self.cli(name); raw=json.dumps(result)
            self.assertNotIn('Invented amber',raw)
            if name=='query-result-contract-checker': self.assertNotIn('SELECT id, label',raw)

    def test_no_database_or_target_actions(self):
        for name in TOOLS:
            _,result=self.cli(name); self.assertFalse(result['sql_executed']); self.assertFalse(result['target_changes_performed'])
        self.assertFalse(list(self.root.glob('*.sqlite*'))); self.assertFalse(list(self.root.glob('*.db')))
