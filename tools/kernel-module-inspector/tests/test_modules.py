from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from module_inspector import inspect,main
import module_inspector
from inspection_support import TextError


def run(deps,load='',available=None,details=False):return inspect(deps.encode(),load.encode(),available.encode() if available is not None else None,details)


class ModuleTests(unittest.TestCase):
    def codes(self,report):return {r['code'] for r in report['findings']}

    def test_dependency_closure_and_order_without_redundant_load_lines(self):
        report=run('demo/core.ko:\ndemo/helper.ko: demo/core.ko\ndemo/feature.ko: demo/helper.ko','feature')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(report['selected_dependency_order'],['module-0001','module-0002','module-0003'])
        self.assertTrue(report['selected_plan_complete_within_metadata'])

    def test_input_order_does_not_override_dependency_order(self):
        report=run('feature.ko: core.ko\ncore.ko:','feature')
        self.assertEqual(report['selected_dependency_order'],['module-0002','module-0001'])

    def test_missing_dependency_blocks_consumer_and_dependants(self):
        report=run('a.ko: absent.ko\nb.ko: a.ko','b')
        self.assertEqual(report['selected_dependency_order'],[])
        self.assertEqual(len(report['blocked_selected_modules']),2)
        self.assertIn('DEPENDENCY_NEEDS_METADATA_REVIEW',self.codes(report))

    def test_cycle_witness_is_closed_and_dependant_not_called_cycle_member(self):
        report=run('a.ko: b.ko\nb.ko: a.ko\nc.ko: a.ko','c')
        witness=report['cycle_witnesses'][0]
        self.assertEqual(witness[0],witness[-1]);self.assertNotIn('module-0003',witness)
        self.assertEqual(len(report['blocked_selected_modules']),3)

    def test_self_cycle(self):
        report=run('a.ko: a.ko','a')
        self.assertEqual(report['cycle_witnesses'],[['module-0001','module-0001']])

    def test_duplicate_metadata_not_arbitrarily_selected(self):
        report=run('a.ko:\na.ko: b.ko\nb.ko:','a')
        self.assertIn('AMBIGUOUS_MODULE_DECLARATION',self.codes(report))
        self.assertFalse(report['selected_plan_complete_within_metadata']);self.assertFalse(report['selected_dependency_order'])

    def test_basename_ambiguity_and_explicit_path(self):
        deps='one/demo.ko:\ntwo/demo.ko:'
        self.assertFalse(run(deps,'demo')['selected_plan_complete_within_metadata'])
        self.assertEqual(run(deps,'one/demo.ko')['selected_dependency_order'],['module-0001'])

    def test_duplicate_declaration_cannot_hide_behind_unique_basename(self):
        report=run('one/demo.ko:\none/demo.ko:\ntwo/demo.ko:','demo')
        self.assertEqual(report['load_entries'][0]['resolution'],'ambiguous_or_unresolved')

    def test_compressed_names_and_no_hyphen_underscore_guessing(self):
        report=run('a-b.ko.xz:\nc.ko.zst: a-b.ko.xz\nd.ko.gz:','c')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.assertIn('LOAD_SELECTION_NEEDS_METADATA_REVIEW',self.codes(run('a-b.ko:','a_b')))

    def test_duplicate_loads_resolve_to_same_module(self):
        report=run('dir/a.ko:','a\ndir/a.ko')
        self.assertEqual(len(report['selected_dependency_order']),1)
        self.assertIn('DUPLICATE_LOAD_SELECTION',self.codes(report))

    def test_missing_load_and_inventory_review(self):
        report=run('dir/a.ko:','not_declared',available='dir/other.ko')
        self.assertIn('LOAD_SELECTION_NEEDS_METADATA_REVIEW',self.codes(report))
        self.assertIn('NOT_IN_SUPPLIED_INVENTORY',self.codes(report))
        self.assertTrue(report['declared_inventory_checked'])

    def test_inventory_duplicates_and_exact_paths(self):
        report=run('dir/a.ko:','a',available='a.ko\na.ko')
        self.assertIn('DUPLICATE_INVENTORY_ENTRY',self.codes(report))
        self.assertIn('NOT_IN_SUPPLIED_INVENTORY',self.codes(report))
        self.assertEqual(run('dir/a.ko:','a',available='dir/a.ko')['status'],'NO_SCOPE_FINDINGS')

    def test_duplicate_dependencies_do_not_corrupt_indegree(self):
        report=run('a.ko:\nb.ko: a.ko a.ko','b')
        self.assertIn('DUPLICATE_DEPENDENCY_TOKEN',self.codes(report))
        self.assertEqual(report['selected_dependency_order'],['module-0001','module-0002'])

    def test_unsupported_syntax_never_silent(self):
        for deps in ('not dependency syntax','a.ko: /absolute.ko','../a.ko:','a.ko: b.ko # inline comment','a.ko: $(shell command)'):
            self.assertTrue(run(deps)['coverage_issues'],deps)
        for load in ('../a','a arg=1','/absolute/a','a\\b'):
            self.assertTrue(run('a.ko:',load)['coverage_issues'],load)

    def test_no_implicit_builtin_or_alias_resolution(self):
        report=run('a.ko: builtin.ko','pci:fictional')
        self.assertTrue(report['coverage_issues']);self.assertIn('DEPENDENCY_NEEDS_METADATA_REVIEW',self.codes(report))

    def test_empty_inputs_and_unselected_cycle(self):
        self.assertEqual(run('','# comment')['status'],'NO_SCOPE_FINDINGS')
        report=run('a.ko: a.ko\nb.ko:','b')
        self.assertEqual(report['selected_dependency_order'],['module-0002'])
        self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_privacy_and_details(self):
        self.assertNotIn('private_module',json.dumps(run('fictional/private_module.ko:','private_module')))
        self.assertIn('private_module',json.dumps(run('fictional/private_module.ko:','private_module',details=True)))

    def test_iterative_deep_graph_and_node_limit(self):
        text='\n'.join(f'm{i}.ko: '+(f'm{i-1}.ko' if i else '') for i in range(1500))
        report=run(text,'m1499')
        self.assertEqual(len(report['selected_dependency_order']),1500)
        with self.assertRaisesRegex(TextError,'MODULE_NODE_LIMIT'):run('\n'.join(f'm{i}.ko:' for i in range(2001)))

    def test_edge_limit(self):
        text='\n'.join(f'a{i}.ko: '+' '.join('b.ko' for _i in range(900)) for i in range(5))
        with self.assertRaisesRegex(TextError,'MODULE_EDGE_LIMIT'):run(text)

    def test_cycle_witness_budget(self):
        with patch.object(module_inspector,'MAX_CYCLE_NODES',2):
            with self.assertRaisesRegex(TextError,'CYCLE_WITNESS_LIMIT'):run('a.ko: b.ko\nb.ko: a.ko','a')

    def test_cli_generated_examples_and_private_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            for name,expected in [('clean',0),('review',1)]:
                result=subprocess.run([sys.executable,'-B',str(ROOT/'module_inspector.py'),'--deps',str(base/f'fixtures/{name}.dep'),'--load-list',str(base/f'fixtures/{name}.load'),'--output',str(base/name)],capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr);self.assertNotIn(str(base),result.stdout)
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture):result=main(['--deps',str(base/'absent-private'),'--load-list',str(base/'fixtures/clean.load'),'--output',str(base/'error')])
            self.assertEqual(result,2);self.assertNotIn('absent-private',capture.getvalue());self.assertFalse((base/'error').exists())


if __name__=='__main__':unittest.main()
