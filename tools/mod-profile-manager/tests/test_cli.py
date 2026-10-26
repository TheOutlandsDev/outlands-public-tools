"""Actual CLI on generated files; no real game installation or private profile."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def catalog(root):
    return {path.relative_to(root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():
            yield from strings(key);yield from strings(item)
    elif isinstance(value,list):
        for item in value:yield from strings(item)


class CliTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name).resolve();self.workspace=self.base/'workspace';self.source=self.base/'source'
        (self.source/'settings').mkdir(parents=True)
        (self.source/'settings/demo.ini').write_bytes(b'[fictional]\nvalue=orchard\n')
        (self.source/'readme.txt').write_bytes(b'Only fictional demo contents\n')
        self.before=catalog(self.source)

    def cli(self,*args,expected=0,optimize=False):
        command=[sys.executable,'-B',*(['-O'] if optimize else []),str(ROOT/'profile_manager.py'),*map(str,args)]
        result=subprocess.run(command,cwd=self.base,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,expected,(result.stdout,result.stderr))
        self.assertFalse(result.stderr,result.stderr)
        return result

    def value(self,*args,expected=0,optimize=False):
        result=self.cli(*args,expected=expected,optimize=optimize)
        value=json.loads(result.stdout)
        for text in strings(value):
            self.assertNotIn(str(self.base).casefold(),text.casefold())
            self.assertNotIn(self.base.as_posix().casefold(),text.casefold())
            self.assertNotIn('Only fictional demo contents',text)
        if expected==2:
            self.assertEqual(set(value),{'status','error'})
            self.assertEqual(value['status'],'INCOMPLETE');self.assertRegex(value['error'],r'^[A-Z][A-Z0-9_]*$')
        return value

    def imported(self):
        self.value('init','--workspace',self.workspace)
        self.value('import-profile','--workspace',self.workspace,'--profile','orchard','--source',self.source)

    def test_no_arguments_and_help_leave_private_tree_unchanged(self):
        before=catalog(self.base)
        for args in ((),('--help',),('activate','--help')):
            with self.subTest(args=args):
                output=self.cli(*args).stdout
                self.assertIn('usage:',output)
        self.assertEqual(catalog(self.base),before)
        self.assertFalse(self.workspace.exists())

    def test_help_does_not_import_engine_gui_or_tk(self):
        code='''import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name in {'profile_engine','profile_gui','tkinter'}:raise RuntimeError('Unexpected application import during help')
    return original(name,*args,**kwargs)
builtins.__import__=guarded
sys.argv=[sys.argv[1],'--help']
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'profile_manager.py')],cwd=self.base,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('usage:',result.stdout)
        self.assertFalse(self.workspace.exists())

    def test_missing_arguments_and_unknown_values_are_fixed_errors(self):
        for args in [('activate',),('not-a-command',),('init','--workspace',self.workspace,'--private-option=fictional-value')]:
            with self.subTest(command=args[0]):
                value=self.value(*args,expected=2)
                self.assertEqual(value['error'],'ARGUMENTS_INVALID')
        self.assertFalse(self.workspace.exists())

    def test_normal_workflow_status_plan_activate_deactivate_recover(self):
        self.imported()
        listed=self.value('list','--workspace',self.workspace)
        self.assertEqual([r['id'] for r in listed['profiles']],['orchard'])
        before=catalog(self.workspace)
        planned=self.value('plan','--workspace',self.workspace,'--action','activate','--profile','orchard')
        self.assertTrue(planned['allowed']);self.assertEqual(catalog(self.workspace),before)
        self.value('activate','--workspace',self.workspace,'--profile','orchard')
        self.assertEqual(catalog(self.workspace/'active'),self.before)
        self.assertEqual(self.value('status','--workspace',self.workspace)['active_profile'],'orchard')
        self.value('deactivate','--workspace',self.workspace)
        self.assertIsNone(self.value('status','--workspace',self.workspace)['active_profile'])
        self.assertFalse((self.workspace/'active').exists())
        self.value('recover','--workspace',self.workspace)
        self.assertEqual(catalog(self.source),self.before)

    def test_actual_optimized_cli_keeps_runtime_safety_guards(self):
        self.imported()
        self.value('activate','--workspace',self.workspace,'--profile','orchard',optimize=True)
        marker=self.workspace/'active/unexpected.txt';marker.write_bytes(b'keep under optimization')
        before=catalog(self.workspace)
        self.value('deactivate','--workspace',self.workspace,expected=2,optimize=True)
        self.assertEqual(catalog(self.workspace),before)
        self.assertEqual(marker.read_bytes(),b'keep under optimization')
        self.assertEqual(catalog(self.source),self.before)

    def test_drift_status_exit_one_and_mutation_refusal(self):
        self.imported();self.value('activate','--workspace',self.workspace,'--profile','orchard')
        (self.workspace/'active/readme.txt').write_bytes(b'drift')
        value=self.value('status','--workspace',self.workspace,expected=1)
        self.assertEqual(value['status'],'REVIEW_REQUIRED')
        self.value('deactivate','--workspace',self.workspace,expected=2)
        self.assertEqual((self.workspace/'active/readme.txt').read_bytes(),b'drift')

    def test_reinitialize_and_duplicate_import_preserve_data(self):
        self.imported();before=catalog(self.workspace)
        self.value('init','--workspace',self.workspace,expected=2)
        self.value('import-profile','--workspace',self.workspace,'--profile','orchard','--source',self.source,expected=2)
        self.assertEqual(catalog(self.workspace),before)

    def test_missing_workspace_or_profile_does_not_create_state(self):
        self.value('status','--workspace',self.workspace,expected=2)
        self.value('activate','--workspace',self.workspace,'--profile','missing',expected=2)
        self.assertFalse(self.workspace.exists())
        self.value('init','--workspace',self.workspace)
        self.value('activate','--workspace',self.workspace,'--profile','missing',expected=2)
        self.assertFalse((self.workspace/'active').exists())

    def test_source_overlap_and_bad_slug_are_refused(self):
        self.value('init','--workspace',self.workspace)
        self.value('import-profile','--workspace',self.workspace,'--profile','../escape','--source',self.source,expected=2)
        self.value('import-profile','--workspace',self.workspace,'--profile','overlap','--source',self.base,expected=2)
        self.assertEqual(self.value('list','--workspace',self.workspace)['profiles'],[])
        self.assertFalse((self.base/'escape').exists())

    def test_tampered_state_is_structured_failure_without_traceback(self):
        self.value('init','--workspace',self.workspace)
        (self.workspace/'state.json').write_bytes(b'{"schema_version":true,"active_profile":null,"pending":null}')
        result=self.cli('status','--workspace',self.workspace,expected=2)
        value=json.loads(result.stdout)
        self.assertEqual(value['status'],'INCOMPLETE')
        self.assertNotIn('Traceback',result.stdout);self.assertNotIn(str(self.workspace),result.stdout)

    def test_public_command_set_has_no_purge_delete_or_fault_option(self):
        for args in [('purge','--workspace',self.workspace),('delete','--workspace',self.workspace),
                     ('activate','--workspace',self.workspace,'--profile','orchard','--fault','after_intent_written')]:
            with self.subTest(command=args[0]):
                value=self.value(*args,expected=2)
                self.assertEqual(value['error'],'ARGUMENTS_INVALID')
        self.assertFalse(self.workspace.exists())

    def test_relative_workspace_is_refused_without_new_folder(self):
        self.value('init','--workspace','relative-store',expected=2)
        self.assertFalse((self.base/'relative-store').exists())


if __name__=='__main__':unittest.main()
