"""Actual four-tool CLI and public-baseline interoperability on fictional series."""
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
TOOLS={'time-series-grid-checker':'grids.py','rolling-origin-backtest-planner':'backtests.py',
       'point-in-time-observation-resolver':'observations.py','feature-window-lineage-checker':'features.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def observation(period,value):
    row=dict(id='sample-p'+str(period),series='sample',period=period,revision=1,available_at=period,value=str(value))
    return dict(row,sha256=sha(encode(row)))

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-timeseries-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        q=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(q.stderr,b''); return q.returncode,json.loads(q.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def run_value(self,name,value):
        file=self.root/(name+'.json'); file.write_bytes(encode(value)); code,result=self.cli(name,file=file)
        self.assertEqual(code,0); return result

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
        for name,key in zip(TOOLS,['coverage','plan','resolutions','lineage']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1); self.assertEqual(result['status'],'REVIEW_REQUIRED')
            if name=='time-series-grid-checker': self.assertEqual(result['coverage'][0]['missing_periods'],[2])
            else: self.assertIsNone(result[key])

    def test_input_pins_and_unchanged_bytes(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes()
            _,result=self.cli(name); self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_and_actual_public_baseline(self):
        values=[2,4,2,4,2,4]; sources=[observation(i,value) for i,value in enumerate(values)]; by_id={row['id']:row for row in sources}
        grid=self.run_value('time-series-grid-checker',dict(format='outlands-time-series-grid-v1',grids=[dict(series='sample',start=0,end=5,step=1)],
            points=[dict(series='sample',period=row['period']) for row in sources]))
        self.assertTrue(grid['coverage_complete'])
        plan=self.run_value('rolling-origin-backtest-planner',dict(format='outlands-rolling-origin-plan-v1',series='sample',grid=dict(start=0,end=5,step=1),
            training=dict(min_points=2,max_points=None,gap_points=0),horizons=[1],stride=1))
        self.assertEqual([row['origin'] for row in plan['plan']],[1,2,3,4])
        requests=[dict(id=f'fold-{fold["fold"]}-p{period}',series='sample',period=period,as_of=fold['origin'])
                  for fold in plan['plan'] for period in range(fold['training_start'],fold['training_end']+1)]
        resolved=self.run_value('point-in-time-observation-resolver',dict(format='outlands-point-in-time-observations-v1',observations=sources,requests=requests))
        refs={row['request_id']:row['observation'] for row in resolved['resolutions']}
        features=[]; histories=[]
        for fold in plan['plan']:
            selected=[refs[f'fold-{fold["fold"]}-p{period}'] for period in range(fold['training_start'],fold['training_end']+1)]
            self.assertTrue(all(row['available_at']<=fold['origin'] for row in selected))
            features.append(dict(id='window-'+str(fold['fold']),series='sample',origin=fold['origin'],target=fold['targets'][0]['period'],
                step=1,lag_points=0,window_points=2,contributors=[dict(id=row['id'],sha256=row['sha256']) for row in selected[-2:]]))
            histories.append(dict(target=fold['targets'][0]['period'],rows=[dict(series='sample',period=row['period'],value=by_id[row['id']]['value']) for row in selected]))
        lineage=self.run_value('feature-window-lineage-checker',dict(format='outlands-feature-window-lineage-v1',observations=sources,features=features))
        self.assertEqual(len(lineage['lineage']),4); self.assertFalse(lineage['feature_values_calculated'])
        file=self.root/'histories.json'; file.write_bytes(encode(histories))
        program='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from ingestion import ingest_csv
from evaluator import forecast
output=[]
for fold in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")):
    body="series,period,value\\n"+"".join(str(r["series"])+","+str(r["period"])+","+str(r["value"])+"\\n" for r in fold["rows"])
    point=forecast(ingest_csv(body),method="last",horizon=1)[0]
    output.append(dict(period=point.period,value=point.value))
print(json.dumps(output))
'''
        q=subprocess.run([sys.executable,'-B','-c',program,str(ROOT/'tools/forecast-baseline-evaluator'),str(file)],cwd=self.root,capture_output=True)
        self.assertEqual(q.returncode,0,q.stderr.decode()); predictions=json.loads(q.stdout)
        self.assertEqual([r['period'] for r in predictions],[2,3,4,5]); self.assertEqual([r['value'] for r in predictions],[4,2,4,2])
        self.assertEqual(sum(abs(row['value']-values[row['period']]) for row in predictions)/len(predictions),2)

    def test_observation_values_not_emitted(self):
        for name in ('point-in-time-observation-resolver','feature-window-lineage-checker'):
            _,result=self.cli(name); self.assertNotIn('"value":',json.dumps(result))
            self.assertFalse(result['availability_authority_verified'])

    def test_no_input_mutation_model_or_target_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['model_trained']); self.assertFalse(result['target_changes_performed'])
