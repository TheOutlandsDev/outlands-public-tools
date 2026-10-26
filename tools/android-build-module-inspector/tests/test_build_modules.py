"""Generated build text only; no Android build tools or real trees. Original MIT."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_module_inspector as tool
from inspection_support import TextError


def bp(text):return [('bp-1',text.encode())]
def mk(text):return [('mk-1',text.encode())]
def report(text,**kwargs):return tool.inspect(bp(text),[],**kwargs)
def make_report(text,**kwargs):return tool.inspect([],mk(text),**kwargs)
def codes(value):return {r['code'] for r in value['coverage_issues']}
def make_module(value='example.alpha',operator=':=',more=''):
    return 'include $(CLEAR_VARS)\nLOCAL_MODULE '+operator+' '+value+'\n'+more+'include $(BUILD_SHARED_LIBRARY)\n'


class BuildTests(unittest.TestCase):
    def test_bp_direct_literal_and_nested_name_not_module(self):
        value=report('cc_library { name: "example.alpha", target: { android: { name: "nested", }, }, }',details=True)
        self.assertEqual(value['status'],'NO_SCOPE_FINDINGS');self.assertEqual(len(value['declarations']),1)
        self.assertEqual(value['declarations'][0]['declared_name'],'example.alpha')

    def test_comments_strings_and_escaped_quotes_do_not_create_declarations(self):
        text='// cc_library { name: "ghost" }\n/* fake { name: "also.ghost" } */\ncc_library { name: "example.alpha", srcs: ["name: \\\"ghost\\\" { }", "// comment", "/* text */"], }'
        value=report(text,details=True);self.assertEqual(value['status'],'NO_SCOPE_FINDINGS')
        self.assertEqual([r['declared_name'] for r in value['declarations']],['example.alpha'])

    def test_multiple_compact_and_multiline_modules(self):
        value=report('cc_library{name:"example.alpha"}\njava_library {\n name:\n"example.beta",\n}\n',details=True)
        self.assertEqual([r['line'] for r in value['declarations']],[1,2]);self.assertEqual(value['status'],'NO_SCOPE_FINDINGS')

    def test_nested_lists_maps_and_trailing_commas(self):
        value=report('cc_library { name:"example.alpha", x:[{ name:"nested", y:[true,false,3], },], }')
        self.assertEqual(value['status'],'NO_SCOPE_FINDINGS')

    def test_duplicate_names_are_review_observation_not_namespace_resolution(self):
        value=report('cc_library{name:"same"}\njava_library{name:"same"}')
        self.assertEqual(value['status'],'REVIEW_REQUIRED');self.assertEqual(value['repeated_names'][0]['count'],2)
        self.assertEqual(value['findings'],[{'code':'REPEATED_DECLARED_NAME_OBSERVED'}])

    def test_duplicate_name_property_same_and_different_held(self):
        for suffix in ('same','different'):
            value=report('cc_library {name:"same",name:"'+suffix+'",}',details=True)
            self.assertTrue(value['declarations'][0]['held']);self.assertIn('BP_DUPLICATE_DIRECT_PROPERTY',codes(value))
            self.assertEqual(value['declarations'][0]['declared_name'],'same' if suffix=='same' else None)

    def test_duplicate_unrelated_direct_property_holds_record(self):
        value=report('cc_library{name:"same",srcs:[],srcs:[]}')
        self.assertTrue(value['declarations'][0]['held']);self.assertIn('BP_DUPLICATE_DIRECT_PROPERTY',codes(value))

    def test_dynamic_missing_invalid_names_hold_unknown_identity(self):
        for body in ('name: prefix + ".suffix"','srcs:[]','name:["name"]','name:"bad name"','name:true'):
            with self.subTest(body=body):
                value=report('cc_library{'+body+'}')
                self.assertTrue(value['unresolved_identity_or_scope']);self.assertTrue(value['declarations'][0]['held'])
                self.assertIn('BP_NAME_UNRESOLVED',codes(value))

    def test_top_level_assignment_stops_remainder_without_guessing_modules(self):
        value=report('cc_library{name:"first"}\nprefix="x"\ncc_library{name:"later"}',details=True)
        self.assertEqual([r['declared_name'] for r in value['declarations']],['first'])
        self.assertIn('BP_TOPLEVEL_REMAINDER_UNINSPECTED',codes(value))

    def test_namespace_and_package_are_unresolved_scope_not_missing_module(self):
        for kind in ('soong_namespace','package'):
            value=report(kind+'{ imports:["unused"], }\ncc_library{name:"same"}')
            self.assertEqual(len(value['declarations']),1);self.assertIn('BP_SCOPE_DECLARATION_UNEVALUATED',codes(value))

    def test_soong_config_named_definition_is_held(self):
        value=report('soong_config_module_type{name:"custom",module_type:"cc_library"}')
        self.assertTrue(value['declarations'][0]['held']);self.assertIn('BP_DYNAMIC_MODULE_KIND_UNEVALUATED',codes(value))

    def test_unclosed_comment_or_quote_produces_coverage(self):
        for text,code in [('/* never closed','BP_UNTERMINATED_COMMENT'),('cc_library{name:"oops','BP_STRING_UNTERMINATED'),('cc_library{name:"a\nb"}','BP_STRING_UNSUPPORTED'),('cc_library{name:"bad\\q"}','BP_STRING_UNSUPPORTED')]:
            with self.subTest(code=code):self.assertIn(code,codes(report(text)))

    def test_delimiter_and_property_malformed_coverage_no_name_guess(self):
        for text in ('cc_library{name:"a",srcs:["x"}}','cc_library{name:"a"','cc_library{name:"a" srcs:[]}','cc_library {"name":"a"}','cc_library {name:}'):
            with self.subTest(text=text):
                value=report(text);self.assertEqual(value['status'],'REVIEW_REQUIRED')
                self.assertFalse(value['declarations'] and not value['declarations'][0]['held'])

    def test_structural_characters_in_string_are_not_tokens(self):
        for text in ('cc_library "{" name:"ghost" }','cc_library "{" name:"ghost", "}"'):
            value=report(text)
            self.assertEqual(value['declarations'],[]);self.assertIn('BP_TOPLEVEL_REMAINDER_UNINSPECTED',codes(value))
        value=report('cc_library { name:"ghost", "}"')
        self.assertEqual(value['declarations'],[]);self.assertIn('BP_PROPERTY_SYNTAX_UNSUPPORTED',codes(value))

    def test_bp_token_depth_identifier_and_string_limits(self):
        cases=[('cc_library{name:"a",x:'+ '['*33+'0'+']'*33+'}','BP_NESTING_LIMIT'),
               ('a'*257+'{}','BP_IDENTIFIER_LIMIT'),('cc_library{name:"'+'a'*1025+'"}','BP_STRING_LIMIT')]
        for text,code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(TextError,'^'+code+'$'):report(text)
        with patch.object(tool,'MAX_TOKENS',2):
            with self.assertRaisesRegex(TextError,'BP_TOKEN_LIMIT'):report('cc_library{name:"a"}')

    def test_make_literal_supported_block_and_other_fields_ignored(self):
        value=make_report('LOCAL_PATH := $(call my-dir)\n'+make_module(more='LOCAL_SRC_FILES := $(LOCAL_PATH)/invented.cpp\n'),details=True)
        self.assertEqual(value['status'],'NO_SCOPE_FINDINGS');self.assertEqual(value['ignored_make_rows'],2)
        self.assertEqual(value['declarations'][0]['declared_name'],'example.alpha')
        self.assertEqual(value['declarations'][0]['module_kind'],'BUILD_SHARED_LIBRARY')

    def test_make_equals_and_literal_hash_comment(self):
        value=make_report(make_module(value='example.alpha # comment',operator='='),details=True)
        self.assertEqual(value['status'],'NO_SCOPE_FINDINGS');self.assertEqual(value['declarations'][0]['declared_name'],'example.alpha')

    def test_make_comment_fake_name_and_string_not_extracted(self):
        value=make_report('# LOCAL_MODULE := ghost\n# include $(CLEAR_VARS)\n'+make_module(more='LOCAL_CFLAGS := "LOCAL_MODULE := hidden"\n'),details=True)
        self.assertEqual([r['declared_name'] for r in value['declarations']],['example.alpha'])

    def test_make_dynamic_quote_and_escaped_hash_names_unsupported(self):
        for value in ('$(variable)','"example.alpha"','example\\#name',''):
            with self.subTest(value=value):
                result=make_report(make_module(value));self.assertTrue(result['declarations'][0]['held'])
                self.assertIn('MK_MODULE_VALUE_UNSUPPORTED',codes(result))

    def test_make_assignment_variants_and_duplicates_held(self):
        for operator in ('+=','?=','::='):
            result=make_report(make_module(operator=operator));self.assertTrue(result['declarations'][0]['held'])
        result=make_report(make_module(more='LOCAL_MODULE := example.alpha\n'))
        self.assertTrue(result['declarations'][0]['held']);self.assertIn('MK_DUPLICATE_MODULE_ASSIGNMENT',codes(result))

    def test_make_build_clear_and_eof_scope_failures(self):
        for text,code in [('LOCAL_MODULE := orphan','MK_MODULE_OUTSIDE_BLOCK'),('include $(BUILD_SHARED_LIBRARY)','MK_BUILD_WITHOUT_CLEAR'),('include $(CLEAR_VARS)\nLOCAL_MODULE := unfinished','MK_BLOCK_WITHOUT_BUILD'),('include $(CLEAR_VARS)\ninclude $(CLEAR_VARS)\n','MK_BLOCK_WITHOUT_BUILD')]:
            with self.subTest(code=code):self.assertIn(code,codes(make_report(text)))

    def test_make_unknown_includes_never_followed_and_hold_block(self):
        for line in ('include $(OTHER_FILE)','include path/elsewhere.mk','-include path/optional.mk','sinclude path/optional.mk'):
            value=make_report(make_module(more=line+'\n'));self.assertTrue(value['declarations'][0]['held'])
            self.assertIn('MK_INCLUDE_UNFOLLOWED',codes(value))

    def test_make_conditional_define_export_and_recipe_stop_remainder(self):
        for prefix in ('ifeq (x,y)','define NAME','export LOCAL_MODULE := nope','\tLOCAL_MODULE := recipe'):
            with self.subTest(prefix=prefix):
                value=make_report(prefix+'\n'+make_module());self.assertEqual(value['declarations'],[])
                self.assertTrue(value['unresolved_identity_or_scope'])

    def test_make_continuation_body_not_extracted(self):
        value=make_report('LOCAL_PATH := \\\nLOCAL_MODULE := ghost\n'+make_module(),details=True)
        self.assertEqual([r['declared_name'] for r in value['declarations']],['example.alpha'])
        self.assertIn('MK_CONTINUATION_UNSUPPORTED',codes(value))
        self.assertIn('MK_CONTINUATION_UNTERMINATED',codes(make_report('LOCAL_PATH := \\')))

    def test_make_unknown_rule_stops_remainder(self):
        value=make_report('target:\n'+make_module());self.assertEqual(value['declarations'],[])
        self.assertIn('MK_UNSUPPORTED_REMAINDER_UNINSPECTED',codes(value))

    def test_wanted_exact_names_no_extension_guess(self):
        value=tool.inspect(bp('cc_library{name:"alpha"}'),mk(make_module('beta')),
                           ('wanted',b'alpha\nbeta\nalpha.so\n'),True)
        self.assertEqual([r['state'] for r in value['wanted']],['observed_once','observed_once','not_observed_selected_supported_scope'])
        self.assertIn({'code':'WANTED_NAME_NOT_OBSERVED'},value['findings'])

    def test_wanted_unmatched_held_when_identity_or_scope_unresolved(self):
        value=report('cc_library{name:dynamic}',wanted=('wanted',b'unseen\n'))
        self.assertEqual(value['wanted'][0]['state'],'held_incomplete_scope')
        self.assertNotIn({'code':'WANTED_NAME_NOT_OBSERVED'},value['findings'])

    def test_wanted_repeat_and_held_match_states(self):
        value=report('cc_library{name:"same"} cc_library{name:"same"} cc_library{name:"held",x:1,x:2}',wanted=('wanted',b'same\nheld\n'))
        self.assertEqual([r['state'] for r in value['wanted']],['observed_multiple','observed_held'])

    def test_wanted_comments_duplicates_invalid_empty(self):
        value=report('cc_library{name:"alpha"}',wanted=('wanted',b'# comment\nalpha\nalpha\n'))
        self.assertEqual(len(value['wanted']),1);self.assertIn('DUPLICATE_WANTED_NAME',codes(value))
        for data,code in ((b'bad name','WANTED_NAME_UNSUPPORTED'),(b'\n# empty','WANTED_NAMES_REQUIRED')):
            with self.assertRaisesRegex(TextError,code):report('',wanted=('wanted',data))

    def test_default_privacy_and_detail_opt_in(self):
        text='custom_module{name:"private.name",srcs:["hidden/path"]}'
        value=report(text,wanted=('wanted',b'private.name\n'))
        encoded=json.dumps(value);self.assertNotIn('private.name',encoded);self.assertNotIn('hidden/path',encoded);self.assertNotIn('custom_module',encoded)
        detailed=json.dumps(report(text,details=True));self.assertIn('private.name',detailed);self.assertIn('custom_module',detailed);self.assertNotIn('hidden/path',detailed)

    def test_utf8_bom_crlf_and_empty_build_text(self):
        value=tool.inspect([('bp',b'\xef\xbb\xbfcc_library {\r\nname:"alpha",\r\n}')],[])
        self.assertEqual(value['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report('')['status'],'NO_SCOPE_FINDINGS')

    def test_coverage_merge_and_declaration_collection_bounds(self):
        with patch.object(tool,'bounded_append',side_effect=TextError('RECORD_LIMIT')):
            with self.assertRaisesRegex(TextError,'RECORD_LIMIT'):report('cc_library{name:"alpha"}')


class CliTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.bp=self.base/'input.bp';self.bp.write_bytes(b'cc_library{name:"example.alpha"}')
        self.mk=self.base/'input.mk';self.mk.write_text(make_module('example.beta'),encoding='utf-8')
        self.wanted=self.base/'wanted.txt';self.wanted.write_bytes(b'example.alpha\nexample.beta\n')
    def run_cli(self,*args):return subprocess.run([sys.executable,'-B',str(ROOT/'build_module_inspector.py'),*map(str,args)],capture_output=True,text=True,check=False)

    def test_actual_cli_multiple_formats_manifest_unchanged_inputs(self):
        before=[p.read_bytes() for p in (self.bp,self.mk,self.wanted)];out=self.base/'report'
        result=self.run_cli('--bp',self.bp,'--mk',self.mk,'--wanted',self.wanted,'--output',out)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['declarations'],2)
        self.assertNotIn(str(self.base),result.stdout+result.stderr)
        self.assertEqual([p.read_bytes() for p in (self.bp,self.mk,self.wanted)],before)
        for row in json.loads((out/'MANIFEST.json').read_text())['files']:
            data=(out/row['path']).read_bytes();self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256']);self.assertEqual(len(data),row['bytes'])
        self.assertNotIn('example.alpha',(out/'report.json').read_text())

    def test_actual_cli_repeat_and_details(self):
        self.bp.write_bytes(b'cc_library{name:"same"} cc_library{name:"same"}')
        result=self.run_cli('--bp',self.bp,'--output',self.base/'repeat','--include-details')
        self.assertEqual(result.returncode,1);self.assertIn('same',(self.base/'repeat/report.json').read_text())

    def test_actual_cli_missing_wanted_and_unknown_hold(self):
        self.wanted.write_bytes(b'unseen')
        result=self.run_cli('--bp',self.bp,'--wanted',self.wanted,'--output',self.base/'unseen')
        self.assertEqual(result.returncode,1)
        self.bp.write_bytes(b'cc_library{name:prefix}')
        result=self.run_cli('--bp',self.bp,'--wanted',self.wanted,'--output',self.base/'held')
        self.assertEqual(result.returncode,1);value=json.loads((self.base/'held/report.json').read_text())
        self.assertEqual(value['wanted'][0]['state'],'held_incomplete_scope')

    def test_actual_cli_same_file_guard_output_existing_and_arguments(self):
        result=self.run_cli('--bp',self.bp,'--mk',self.bp,'--output',self.base/'duplicate')
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error'],'DUPLICATE_INPUT_FILE')
        result=self.run_cli('--bp',self.bp,'--output',self.base)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error'],'OUTPUT_EXISTS')
        result=self.run_cli('--output',self.base/'empty')
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error'],'BUILD_INPUT_REQUIRED')
        result=self.run_cli('--private-unknown=value');self.assertEqual(result.returncode,2)

    def test_actual_cli_invalid_encoding_control_and_input_limit(self):
        for index,data in enumerate((b'\xff',b'\0',b'x'*(1024*1024+1))):
            self.bp.write_bytes(data);result=self.run_cli('--bp',self.bp,'--output',self.base/f'bad{index}')
            self.assertEqual(result.returncode,2);self.assertNotIn(str(self.bp),result.stdout+result.stderr)

    def test_example_generator_documented_paths_and_no_overwrite(self):
        dest=self.base/'examples';command=[sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(dest)]
        first=subprocess.run(command,capture_output=True,text=True,check=False);self.assertEqual(first.returncode,0,first.stderr)
        result=self.run_cli('--bp',dest/'clean.bp','--mk',dest/'clean.mk','--wanted',dest/'wanted.txt','--output',self.base/'clean')
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads((self.base/'clean/report.json').read_text());self.assertEqual(len(value['declarations']),3)
        result=self.run_cli('--bp',dest/'review.bp','--wanted',dest/'wanted-unseen.txt','--output',self.base/'review')
        self.assertEqual(result.returncode,1);value=json.loads((self.base/'review/report.json').read_text())
        self.assertEqual([r['state'] for r in value['wanted']],['observed_multiple','held_incomplete_scope'])
        again=subprocess.run(command,capture_output=True,text=True,check=False);self.assertEqual(again.returncode,2)


if __name__=='__main__':unittest.main()
