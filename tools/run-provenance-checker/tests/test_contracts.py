import copy
import unittest
import run_core as c
import toolkit as t


class Contracts(unittest.TestCase):
    def setUp(self):
        self.value=dict(format='outlands-run-artifact-manifest-v1',run_id='sample-run',artifacts=[
            dict(id='source',role='input',bytes=7,sha256=t.digest(b'sample\n'))])

    def refused(self):
        with self.assertRaises(t.Rejected): c.manifest(t.encode(self.value))

    def test_paths_and_unknown_metadata_forbidden(self):
        self.value['artifacts'][0]['path']='invented/private.txt'; self.refused()

    def test_boolean_size_and_uppercase_hash_refused(self):
        self.value['artifacts'][0]['bytes']=True; self.refused()
        self.value['artifacts'][0]['bytes']=7; self.value['artifacts'][0]['sha256']='A'*64; self.refused()

    def test_role_types_and_invalid_ids_refused(self):
        for role in (True,[],{},'operational'):
            self.value['artifacts'][0]['role']=role; self.refused()
        self.value['artifacts'][0]['role']='input'; self.value['run_id']='../run'; self.refused()

    def test_duplicate_and_excess_artifacts(self):
        self.value['artifacts']*=2; self.refused()
        self.value['artifacts']=[dict(id='item-'+str(i),role='input',bytes=0,sha256=t.digest(b'')) for i in range(17)]
        self.refused()

    def test_declared_aggregate_bound(self):
        self.value['artifacts']=[dict(id='item-'+str(i),role='input',bytes=t.MAX_INPUT,sha256=t.digest(b'')) for i in range(5)]
        self.refused()

    def test_exact_buffer_coverage_and_types(self):
        for values in ({},{'extra':b'sample'},{'source':'sample'}):
            with self.assertRaises(t.Rejected): c.buffers(values,{'source'})

    def test_actual_aggregate_bound(self):
        with self.assertRaises(t.Rejected): c.buffers({str(i):b'x'*t.MAX_INPUT for i in range(5)},set(map(str,range(5))))

    def test_portable_name_refusal(self):
        for value in ('../a','a/b','a\\b','a:stream','CON.txt','LPT0.json','a..b','a.txt.','café.txt','a'*81):
            with self.subTest(value=value),self.assertRaises(t.Rejected): c.public_name(value)

    def test_public_name_case_collisions(self):
        with self.assertRaisesRegex(t.Rejected,'PUBLIC_NAME_COLLISION'):
            c.selected_names({'a':dict(public_name='Sample.txt',sha256='0'*64),'b':dict(public_name='sample.TXT',sha256='0'*64)})

    def test_observation_is_deterministic_and_has_no_paths(self):
        before=copy.deepcopy(self.value)
        _,rows=c.manifest(t.encode(self.value)); observed,issues=c.observe(rows,{'source':b'sample\n'})
        self.assertFalse(issues); self.assertEqual(observed,[dict(id='source',bytes=7,sha256=t.digest(b'sample\n'))])
        self.assertEqual(before,self.value)
