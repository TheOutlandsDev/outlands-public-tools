"""Generated badging text only, including the actual Python CLI."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import apk_report_diff as tool
from inspection_support import TextError

BASE="package: name='example.orchard' versionCode='1' versionName='1.0'\nsdkVersion:'23'\ntargetSdkVersion:'34'\n"
def data(extra='',base=BASE): return (base+extra).encode('utf-8')
def changes(before,after,details=True): return tool.compare(before,after,details)


class ParseTests(unittest.TestCase):
    def test_same_supported_report(self):
        result=changes(data(),data()); self.assertEqual(result['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual(result['package_identity'],'same_declared_name')

    def test_package_attribute_order_and_spaces(self):
        other="package:\tversionName='1.0' name='example.orchard'   versionCode='1'\nsdkVersion:'23'\ntargetSdkVersion:'34'\n"
        self.assertEqual(changes(data(),other.encode())['changes'],[])

    def test_version_strings_preserved_no_numeric_conversion(self):
        before=data(base=BASE.replace("versionCode='1'","versionCode='9007199254740993'"))
        after=data(base=BASE.replace("versionCode='1'","versionCode='9007199254740994'"))
        row=changes(before,after)['changes'][0]
        self.assertEqual(row['before'],'9007199254740993'); self.assertEqual(row['after'],'9007199254740994')

    def test_version_name_spaces_equals_and_html(self):
        other=data(base=BASE.replace("versionName='1.0'","versionName='alpha = <demo>'"))
        self.assertEqual(changes(data(),other)['changes'][0]['after'],'alpha = <demo>')

    def test_empty_version_name_supported(self):
        other=data(base=BASE.replace("versionName='1.0'","versionName=''"))
        self.assertEqual(changes(data(),other)['changes'][0]['after'],'')

    def test_package_ignored_build_fields(self):
        other=data(base=BASE.replace("versionName='1.0'","versionName='1.0' platformBuildVersionCode='35' compileSdkVersion='35'"))
        self.assertEqual(changes(data(),other)['status'],'NO_SCOPE_FINDINGS')

    def test_package_unknown_split_attribute_holds_all(self):
        other=data(base=BASE.replace("versionName='1.0'","versionName='2' split='config.demo'"))
        result=changes(data(),other); self.assertEqual(result['changes'],[])
        self.assertEqual(result['package_identity'],'unresolved')

    def test_duplicate_package_even_identical_holds(self):
        result=changes(data(),data(BASE.splitlines()[0]+'\n'))
        self.assertEqual(result['changes'],[]); self.assertTrue(result['coverage_issues'])

    def test_package_rename_not_compared_as_upgrade(self):
        result=changes(data(),data(base=BASE.replace('example.orchard','example.meadow').replace("versionCode='1'","versionCode='2'")))
        self.assertEqual(result['changes'],[]); self.assertEqual(result['package_identity'],'different_declared_names')
        self.assertEqual(result['findings'],[{'code':'PACKAGE_IDENTITY_CHANGED'}])

    def test_missing_package_is_coverage(self):
        result=changes(data(),b"sdkVersion:'23'\n")
        self.assertEqual(result['changes'],[]); self.assertEqual(result['status'],'REVIEW_REQUIRED')

    def test_invalid_package_attribute_syntax(self):
        for line in ("package: name='example.orchard' versionCode='1' versionName='x' trailing",
                     'package: name="example.orchard" versionCode=\'1\' versionName=\'x\'',
                     "package: name='example.orchard' name='example.other' versionCode='1' versionName='x'",
                     "package: name='example.orchard' versionCode='-1' versionName='x'",
                     "package: name='example.orchard' versionCode='1.0' versionName='x'",
                     "package: name='example.orchard' versionCode='1' versionName='a\\b'",
                     "package: name='example.orchard' versionCode='1' versionName='a'b'",
                     "package: name='single' versionCode='1' versionName='x'"):
            with self.subTest(line=line):
                result=changes(data(),(line+'\n').encode()); self.assertEqual(result['changes'],[])
                self.assertEqual(result['package_identity'],'unresolved')

    def test_package_lengths(self):
        for value in ('a.'+'b'*255,'a.'+'b'*1023):
            self.assertEqual(changes(data(),data(base=BASE.replace('example.orchard',value)))['package_identity'],'unresolved')

    def test_sdk_min_target_max_changes(self):
        before=data("maxSdkVersion:'34'\n")
        after=data("maxSdkVersion:'35'\n",BASE.replace("sdkVersion:'23'","sdkVersion:'24'").replace("targetSdkVersion:'34'","targetSdkVersion:'35'"))
        self.assertEqual({r['field'] for r in changes(before,after)['changes']},{'min_sdk','target_sdk','max_sdk'})

    def test_sdk_absence_is_unspecified(self):
        result=changes(data(),data("maxSdkVersion:'35'\n"))
        self.assertEqual(result['changes'][0]['before'],None)
        self.assertEqual(result['changes'][0]['after'],'35')

    def test_sdk_codenames_held_not_absence(self):
        result=changes(data(),data(base=BASE.replace("targetSdkVersion:'34'","targetSdkVersion:'VanillaIceCream'")))
        self.assertEqual(result['changes'],[])
        self.assertEqual(result['held_comparisons'][0]['field'],'target_sdk')

    def test_unknown_opposite_rows_hold_unmatched_sdk(self):
        other=data(base=BASE.replace("targetSdkVersion:'34'","targetSdkVersion : '35'"))
        result=changes(data(),other); self.assertEqual(result['changes'],[])
        self.assertTrue(any(r.get('field')=='target_sdk' and r['reason']=='UNIDENTIFIED_OPPOSITE_ROWS' for r in result['held_comparisons']))

    def test_combined_coverage_collection_bound(self):
        value=data('future: fictional\n'*2100)
        with self.assertRaisesRegex(TextError,'RECORD_LIMIT'): changes(value,value)

    def test_duplicate_sdk_even_identical_held(self):
        result=changes(data(),data("sdkVersion:'23'\n"))
        self.assertEqual(result['changes'],[]); self.assertTrue(result['held_comparisons'])

    def test_leading_zeroes_are_literal(self):
        result=changes(data(),data(base=BASE.replace("sdkVersion:'23'","sdkVersion:'023'")))
        self.assertEqual(result['changes'][0]['after'],'023')

    def test_library_add_remove_and_requirement(self):
        before=data("uses-library:'example.alpha'\nuses-library:'example.beta'\n")
        after=data("uses-library-not-required:'example.alpha'\nuses-library:'example.gamma'\n")
        result=changes(before,after)
        self.assertEqual(len(result['changes']),3)
        self.assertEqual(result['changes'][0]['before'],'required')
        self.assertEqual(result['changes'][0]['after'],'optional')

    def test_library_duplicate_same_kind_held(self):
        before=data("uses-library:'example.alpha'\nuses-library:'example.alpha'\n")
        result=changes(before,data())
        self.assertEqual(result['changes'],[]); self.assertTrue(result['held_comparisons'])

    def test_library_conflicting_kind_held(self):
        before=data("uses-library:'example.alpha'\nuses-library-not-required:'example.alpha'\n")
        self.assertEqual(changes(before,data())['changes'],[])

    def test_unsupported_known_library_holds_identity(self):
        before=data("uses-library:'example.alpha'\n")
        for extra in ("uses-library:'example.alpha' extra='x'\n", "uses-library:'example.alpha'garbage\n"):
            result=changes(before,data(extra)); self.assertEqual(result['changes'],[])
            self.assertTrue(any(r['reason']=='AMBIGUOUS_LIBRARY_IDENTITY' for r in result['held_comparisons']))

    def test_unknown_rows_hold_unmatched_not_supported_matched(self):
        before=data("uses-library:'example.alpha'\nuses-library:'example.beta'\n")
        after=data("uses-library-not-required:'example.alpha'\nfuture-row: private unknown\n")
        result=changes(before,after)
        self.assertEqual(len(result['changes']),1)
        self.assertEqual(result['changes'][0]['declared_identity'],'example.alpha')
        self.assertTrue(any(r['reason']=='UNIDENTIFIED_OPPOSITE_ROWS' for r in result['held_comparisons']))

    def test_malformed_unknown_library_holds_unmatched(self):
        result=changes(data("uses-library:'example.alpha'\n"),data("uses-library:'bad value'\n"))
        self.assertEqual(result['changes'],[])

    def test_implied_library_is_explicit_coverage(self):
        result=changes(data(),data("uses-implied-library:'example.alpha' reason='fiction'\n"))
        self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertEqual(result['summaries']['after']['unidentified_rows'],1)

    def test_common_library_relative_order(self):
        before=data("uses-library:'example.alpha'\nuses-library:'example.beta'\n")
        after=data("uses-library:'example.beta'\nuses-library:'example.alpha'\n")
        row=changes(before,after)['changes'][0]
        self.assertEqual(row['field'],'relative_common_order'); self.assertEqual(row['before'],['example.alpha','example.beta'])

    def test_new_library_does_not_falsely_reorder_common(self):
        before=data("uses-library:'example.alpha'\nuses-library:'example.beta'\n")
        after=data("uses-library:'example.alpha'\nuses-library:'example.gamma'\nuses-library:'example.beta'\n")
        self.assertEqual([r['field'] for r in changes(before,after)['changes']],['declared_requirement'])

    def test_known_out_of_scope_rows_omitted(self):
        extra="application: label='Private Application' icon='private.png'\napplication-label-en:'Private'\nuses-permission: name='example.PRIVATE'\nnative-code: 'fictional-abi'\n"
        result=changes(data(),data(extra),False)
        encoded=json.dumps(result)
        self.assertEqual(result['status'],'NO_SCOPE_FINDINGS'); self.assertNotIn('Private',encoded)
        self.assertEqual(result['summaries']['after']['ignored_rows'],4)

    def test_default_omits_package_version_library_and_unknown_values(self):
        before=data("uses-library:'example.alpha'\n")
        after=data("future-row: secret-marker\n",BASE.replace("versionName='1.0'","versionName='private-version'"))
        encoded=json.dumps(changes(before,after,False))
        for value in ('example.orchard','example.alpha','private-version','secret-marker'):
            self.assertNotIn(value,encoded)

    def test_unknown_raw_values_omitted_even_details(self):
        self.assertNotIn('private-marker',json.dumps(changes(data(),data('future: private-marker\n'))))

    def test_bom_crlf_blank_lines(self):
        other=b'\xef\xbb\xbf'+data().replace(b'\n',b'\r\n')+b'\r\n'
        self.assertEqual(changes(data(),other)['status'],'NO_SCOPE_FINDINGS')

    def test_control_encoding_and_line_budgets(self):
        for value in (b'\xff',data()+b'\0',data()+b'\r',data()+b'x'*8193,b'\n'*20000,b'a'*1048577):
            with self.subTest(length=len(value)):
                with self.assertRaises(TextError): changes(data(),value)

    def test_record_budget(self):
        value=data(''.join(f"uses-library:'example.lib{i}'\n" for i in range(4001)))
        with self.assertRaisesRegex(TextError,'RECORD_LIMIT'): changes(data(),value)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve(); self.before=self.base/'before.txt'; self.after=self.base/'after.txt'
        self.before.write_bytes(data()); self.after.write_bytes(data())

    def run_cli(self,output='report',extra=()):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'apk_report_diff.py'),
            '--before',str(self.before),'--after',str(self.after),'--output',str(self.base/output),*extra],
            capture_output=True,text=True,check=False)
        self.assertEqual(result.stderr,''); return result

    def test_cli_equal_fresh_reports_and_input_bytes(self):
        result=self.run_cli(); self.assertEqual(result.returncode,0)
        report=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS'); self.assertEqual(self.before.read_bytes(),data())
        self.assertEqual(self.after.read_bytes(),data()); self.assertNotIn(str(self.base),result.stdout)
        for row in json.loads((self.base/'report/MANIFEST.json').read_text())['files']:
            value=(self.base/'report'/row['path']).read_bytes()
            self.assertEqual(row['sha256'],hashlib.sha256(value).hexdigest()); self.assertEqual(row['bytes'],len(value))

    def test_cli_change_exit_details_html_escaped(self):
        self.after.write_bytes(data(base=BASE.replace("versionName='1.0'","versionName='<script>demo</script>'")))
        result=self.run_cli(extra=['--include-details']); self.assertEqual(result.returncode,1)
        html=(self.base/'report/report.html').read_text(); self.assertIn('&lt;script&gt;',html); self.assertNotIn('<script>demo',html)

    def test_cli_coverage_exit(self):
        self.after.write_bytes(data('future: private\n')); self.assertEqual(self.run_cli().returncode,1)

    def test_cli_output_refuses_existing(self):
        self.assertEqual(self.run_cli().returncode,0); result=self.run_cli(); self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'OUTPUT_EXISTS')

    def test_cli_input_failure_no_output(self):
        self.after.write_bytes(b'\xff'); result=self.run_cli(); self.assertEqual(result.returncode,2)
        self.assertFalse((self.base/'report').exists()); self.assertNotIn(str(self.after),result.stdout)

    def test_cli_duplicate_input(self):
        result=self.run_cli(extra=['--after',str(self.before)])
        self.assertEqual(result.returncode,2); self.assertEqual(json.loads(result.stdout)['error'],'DUPLICATE_INPUT_FILE')

    def test_cli_relative_input(self):
        result=self.run_cli(extra=['--before','relative.txt']); self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'LOCAL_ABSOLUTE_PATH_REQUIRED')

    def test_cli_invalid_args_fixed_error(self):
        result=self.run_cli(extra=['--unknown=private']); self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'ARGUMENTS_INVALID'); self.assertNotIn('private',result.stdout)

    def test_documented_generator_and_six_changes(self):
        command=[sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(self.base/'demo')]
        generated=subprocess.run(command,capture_output=True,text=True,check=False)
        self.assertEqual(generated.returncode,0,generated.stdout+generated.stderr)
        result=self.run_cli(extra=['--before',str(self.base/'demo/before.txt'),'--after',str(self.base/'demo/after.txt'),'--include-details'])
        self.assertEqual(result.returncode,1)
        report=json.loads((self.base/'report/report.json').read_text())
        self.assertEqual(len(report['changes']),6); self.assertEqual(report['coverage_issues'],[])
        repeat=subprocess.run(command,capture_output=True,text=True,check=False)
        self.assertEqual(repeat.returncode,2); self.assertEqual(json.loads(repeat.stdout)['error'],'OUTPUT_EXISTS')


if __name__=='__main__': unittest.main()
