"""Actual independent CLIs and fictional connected unit conversion cases."""
import copy
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'tools'
TOOLS={'unit-catalog-contract-checker':'catalogs.py','conversion-path-checker':'paths.py','quantity-conversion-reconciler':'quantities.py','unit-revision-scenario-comparator':'scenarios.py'}
def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def fixture(name):return json.loads((ROOT/name/'examples/input.json').read_text(encoding='utf-8'))
def cli(name,value=None,example='input'):
    folder=ROOT/name
    if value is None:path=folder/'examples'/(example+'.json');return invoke(name,path)
    with tempfile.TemporaryDirectory(prefix='fictional-unit-check-') as temp:
        path=Path(temp)/'input.json';path.write_bytes(encode(value));return invoke(name,path)
def invoke(name,path):
    q=subprocess.run([sys.executable,'-B',str(ROOT/name/TOOLS[name]),'--input',str(path)],capture_output=True,text=True)
    if q.stderr:raise AssertionError(q.stderr)
    return q.returncode,json.loads(q.stdout)

class UnitIntegrity(unittest.TestCase):
    def test_four_independent_sources_and_examples(self):
        for name in TOOLS:
            q=subprocess.run([sys.executable,'-B',str(ROOT/name/'source_check.py')],capture_output=True,text=True)
            self.assertEqual(q.returncode,0,q.stderr+q.stdout)
            self.assertEqual(json.loads(q.stdout)['status'],'SOURCE_MATCH')
            code,result=cli(name)
            self.assertEqual(code,1 if name=='unit-revision-scenario-comparator' else 0)
            self.assertEqual(result['status'],'REVIEW_REQUIRED' if code else 'PASS')

    def test_connected_exact_factors_and_quantities(self):
        code,paths=cli('conversion-path-checker');self.assertEqual(code,0)
        factors=paths['assessment'][0]['factors_to_base']
        self.assertEqual(factors['foot'],'381/1250')
        self.assertEqual(factors['centimeter'],'1/100')
        self.assertEqual(factors['kilobyte'],'1000/1')
        code,claims=cli('quantity-conversion-reconciler');self.assertEqual(code,0)
        self.assertEqual({r['id']:r['expected']['value'] for r in claims['assessment']},{'hvac_duct':'76.2','software_chunk':'1500'})

    def test_consistent_alternate_path(self):
        name='conversion-path-checker';value=fixture(name)
        value['catalogs'][0]['edges'].append({'id':'direct_inch_meter','source':'inch','target':'meter','numerator':127,'denominator':5000})
        code,result=cli(name,value);self.assertEqual(code,0,result)
        self.assertEqual(result['assessment'][0]['factors_to_base']['inch'],'127/5000')

    def test_hundred_fictional_conversions_against_decimal_reference(self):
        name='quantity-conversion-reconciler';value=fixture(name)
        factor={'meter':Fraction(1),'centimeter':Fraction(1,100),'inch':Fraction(127,5000),'foot':Fraction(381,1250)}
        rng=random.Random(93);claims=[]
        for index in range(100):
            source,target=rng.sample(list(factor),2)
            supplied=Decimal(rng.randrange(-10000,10001))/100
            exact=Fraction(supplied)*factor[source]/factor[target]
            reference=(Decimal(exact.numerator)/Decimal(exact.denominator)).quantize(Decimal('0.01'),rounding=ROUND_HALF_EVEN)
            claim=copy.deepcopy(value['claims'][0]);claim.update(id=f'trial_{index:03d}',source=source,target=target,input=str(supplied),output=str(reference),places=2,rounding='half_even')
            claims.append(claim)
        value['claims']=claims
        code,result=cli(name,value);self.assertEqual(code,0,result)
        self.assertEqual(len(result['assessment']),100)

    def test_conflicting_and_disconnected_paths_withhold_factors(self):
        name='conversion-path-checker';value=fixture(name)
        value['catalogs'][0]['edges'].append({'id':'wrong_direct','source':'foot','target':'meter','numerator':1,'denominator':1})
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIn('PATH_CONFLICT',[i['code'] for i in result['issues']]);self.assertIsNone(result['assessment'][0]['factors_to_base'])
        value=fixture(name);value['catalogs'][0]['edges']=[e for e in value['catalogs'][0]['edges'] if e['id']!='inch_per_foot']
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIn('UNIT_UNREACHABLE',[i['code'] for i in result['issues']]);self.assertIsNone(result['qualified_scope_sha256'])

    def test_rounding_ties_and_negative_values(self):
        name='quantity-conversion-reconciler'
        for source_value,mode,expected in [('50','half_even','0'),('50','half_away','1'),('-50','half_even','0'),('-50','half_away','-1')]:
            value=fixture(name);claim=value['claims'][0];claim.update(source='centimeter',target='meter',input=source_value,output=expected,places=0,rounding=mode);value['claims']=[claim]
            code,result=cli(name,value);self.assertEqual(code,0,result)
            self.assertEqual(result['assessment'][0]['expected']['value'],expected)

    def test_false_pin_and_wrong_output_withhold_qualification(self):
        name='quantity-conversion-reconciler';value=fixture(name)
        value['claims'][0]['catalog_sha256']='0'*64
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIsNone(result['assessment']);self.assertIsNone(result['qualified_scope_sha256'])
        value=fixture(name);value['claims'][0]['output']='76.21'
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIn('CONVERSION_MISMATCH',[i['code'] for i in result['issues']])

    def test_same_revision_changed_catalog_withheld(self):
        name='unit-revision-scenario-comparator';value=fixture(name)
        candidate=value['candidate_catalogs'][0];candidate['revision']=1
        for case in value['scenarios']:case['candidate_revision']=1;case['candidate_sha256']=pin(candidate)
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIn('SAME_REVISION_CATALOG_CONFLICT',[i['code'] for i in result['issues']])
        self.assertIsNone(result['assessment'])

    def test_structural_refusals_and_review_examples(self):
        for name in TOOLS:
            code,result=cli(name,example='needs-review');self.assertEqual(code,1)
            self.assertIsNone(result['qualified_scope_sha256'])
        name='unit-catalog-contract-checker';value=fixture(name)
        value['catalogs'][0]['edges'][0]['offset']=1
        code,result=cli(name,value);self.assertEqual(code,1)
        self.assertIn('FIELDS_INVALID',[i['code'] for i in result['issues']])
        with tempfile.TemporaryDirectory(prefix='fictional-unit-check-') as temp:
            path=Path(temp)/'bad.json';path.write_text('{"format":"a","format":"b"}',encoding='utf-8')
            code,result=invoke(name,path)
        self.assertEqual(code,2);self.assertEqual(result['code'],'JSON_DUPLICATE_KEY')

if __name__=='__main__':unittest.main()
