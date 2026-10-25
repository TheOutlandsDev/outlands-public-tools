from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import builtins
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'examples'))
import generate as fixtures
import vintf_inspector as tool
from inspection_support import TextError


def manifest(content,kind='device',version='2.0'):
    return f'<manifest version="{version}" type="{kind}">{content}</manifest>'


def hidl(fqname='@2.1::IDemo/default',extra='',transport='<transport>hwbinder</transport>'):
    return '<hal><name>example.hardware.demo</name>'+transport+f'<fqname>{fqname}</fqname>'+extra+'</hal>'


def run(current,before=None,details=False):
    return tool.inspect([('unused',current.encode())],None if before is None else [('unused',before.encode())],details)


class VintfTests(unittest.TestCase):
    def codes(self,report,coverage=False):return {r['code'] for r in report['coverage_issues' if coverage else 'findings']}

    def test_clean_hidl_aidl_and_opt_in_details(self):
        text=fixtures.FILES['clean.xml'];report=run(text)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(len(report['declarations']),2)
        self.assertNotIn('example.hardware',json.dumps(report));self.assertNotIn('IDemo',json.dumps(report))
        self.assertEqual(run(text,details=True)['declarations'][0]['fields']['version'],'2.1')

    def test_equivalent_forms_and_comments_not_changes(self):
        report=run(fixtures.FILES['same.xml'],fixtures.FILES['clean.xml'])
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertFalse(report['changes'])

    def test_transport_and_arch_change(self):
        report=run(manifest(hidl(transport='<transport arch="64">passthrough</transport>')),manifest(hidl()))
        self.assertEqual(report['changes'][0]['kind'],'changed')
        self.assertEqual(report['changes'][0]['fields_changed'],['transport','arch'])

    def test_version_change_is_remove_add(self):
        report=run(manifest(hidl('@2.2::IDemo/default')),manifest(hidl()))
        self.assertEqual([r['kind'] for r in report['changes']],['removed','added'])

    def test_removed_and_added_instance(self):
        report=run(manifest(hidl('@2.1::IDemo/alternate')),manifest(hidl()))
        self.assertEqual(len(report['changes']),2)

    def test_duplicates_are_ambiguous_not_arbitrarily_paired(self):
        report=run(manifest(hidl()+hidl()),manifest(hidl()))
        self.assertEqual(len(report['ambiguous_comparisons']),1);self.assertFalse(report['changes'])
        self.assertIn('REPEATED_SELECTED_DECLARATION',self.codes(report))

    def test_duplicate_transport_conflict(self):
        report=run(manifest(hidl()+hidl(transport='<transport arch="32">passthrough</transport>')))
        self.assertIn('CONFLICTING_SELECTED_DECLARATION',self.codes(report))

    def test_explicit_selected_fragments_only(self):
        report=tool.inspect([('a',manifest(hidl()).encode()),('b',manifest(hidl()).encode())])
        self.assertIn('REPEATED_SELECTED_DECLARATION',self.codes(report))
        self.assertEqual(len(report['inputs']),2)

    def test_device_and_framework_are_distinct_identities(self):
        report=tool.inspect([('a',manifest(hidl()).encode()),('b',manifest(hidl(),kind='framework').encode())])
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_no_override_or_levels_simulation(self):
        text=manifest(hidl().replace('<hal>','<hal override="true" max-level="7">'))
        report=run(text)
        self.assertIn('HAL_MODIFIERS_NOT_EVALUATED',self.codes(report,True));self.assertEqual(len(report['declarations']),1)

    def test_unsupported_root_metadata_and_native(self):
        for text in ('<compatibility-matrix/>',manifest(hidl(),version='3.0'),'<manifest version="2.0"/>',manifest('<hal format="native"><name>Demo</name></hal>')):
            report=run(text);self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertTrue(report['coverage_issues'])

    def test_namespace_xinclude_and_no_resource_following(self):
        report=run('<manifest xmlns="urn:fiction" version="2.0" type="device"/>')
        self.assertIn('UNSUPPORTED_XML_NAMESPACE',self.codes(report,True))
        report=run(manifest('<x:include xmlns:x="http://www.w3.org/2001/XInclude" href="file:///fictional/not-opened.xml"/>'))
        self.assertIn('UNSUPPORTED_XML_NAMESPACE',self.codes(report,True))

    def test_pi_is_coverage_comments_are_ignored(self):
        self.assertEqual(run('<!-- fiction -->'+manifest(hidl()))['status'],'NO_SCOPE_FINDINGS')
        self.assertIn('PROCESSING_INSTRUCTION_UNINSPECTED',self.codes(run('<?fiction instruction?>'+manifest(hidl())),True))

    def test_dtd_entity_and_non_utf8_declaration_rejected(self):
        for text in ('<!DOCTYPE manifest [<!ENTITY a "fiction">]>'+manifest(''),'<!DOCTYPE manifest SYSTEM "file:///fictional/not-opened">'+manifest(''),'< !ENTITY bad>'):
            with self.assertRaises(TextError):run(text)
        with self.assertRaisesRegex(TextError,'XML_UTF8_DECLARATION_REQUIRED'):run('<?xml version="1.0" encoding="iso-8859-1"?>'+manifest(''))

    def test_invalid_xml_and_no_native_parser_import(self):
        with self.assertRaisesRegex(TextError,'INVALID_XML'):run('<manifest>')
        original=builtins.__import__
        def guard(name,*args,**kwargs):
            if name.split('.')[0] in {'xml','pyexpat','_elementtree'}:raise AssertionError('Native parser import')
            return original(name,*args,**kwargs)
        with patch.object(builtins,'__import__',side_effect=guard):
            self.assertEqual(run(manifest(hidl()))['status'],'NO_SCOPE_FINDINGS')

    def test_structure_depth_and_node_limits(self):
        with self.assertRaisesRegex(TextError,'XML_STRUCTURE_LIMIT'):run(manifest('<a>'*33+'</a>'*33))
        text='<manifest version="2.0" type="device">\n'+('\n'.join('<x/>' for _i in range(8001)))+'\n</manifest>'
        with self.assertRaisesRegex(TextError,'XML_STRUCTURE_LIMIT'):run(text)

    def test_attribute_limits(self):
        text='<manifest version="2.0" type="device" '+ ' '.join(f'a{i}="x"' for i in range(17))+'/>'
        with self.assertRaisesRegex(TextError,'XML_ATTRIBUTE_LIMIT'):run(text)

    def test_missing_repeated_scalar_and_bad_names(self):
        for content in (hidl().replace('<name>example.hardware.demo</name>',''),hidl().replace('</name>','</name><name>example.other</name>',1),hidl().replace('example.hardware.demo','not a package'),hidl('@bad::IDemo/default'),hidl('@2.1::bad-name/default')):
            self.assertTrue(run(manifest(content))['coverage_issues'])

    def test_hidl_fqname_version_independent_of_version_elements(self):
        report=run(manifest(hidl(extra='<version>1.0</version>')),details=True)
        self.assertEqual(report['declarations'][0]['fields']['version'],'2.1')

    def test_explicit_versions_for_interface_and_aidl(self):
        interface='<interface><name>IDemo</name><instance>default</instance></interface>'
        report=run(manifest('<hal><name>example.hardware.demo</name><transport>hwbinder</transport><version>1.0</version><version>2.1</version>'+interface+'</hal>'))
        self.assertEqual(len(report['declarations']),2)
        for content in ('<hal format="aidl"><name>example.hardware.demo</name><fqname>IDemo/default</fqname></hal>','<hal><name>example.hardware.demo</name><transport>hwbinder</transport>'+interface+'</hal>'):
            self.assertTrue(run(manifest(content))['coverage_issues'])

    def test_aidl_meta_version_and_transport_limit(self):
        text='<hal format="aidl"><name>example.hardware.demo</name><version>1</version><fqname>IDemo/default</fqname></hal>'
        self.assertTrue(run(manifest(text,version='1.0'))['coverage_issues'])
        text=text.replace('<version>','<transport ip="fictional" port="123">inet</transport><version>')
        self.assertIn('AIDL_TRANSPORT_UNINSPECTED',self.codes(run(manifest(text)),True))

    def test_unknown_elements_and_regex_instances_require_review(self):
        text='<hal><name>example.hardware.demo</name><transport>hwbinder</transport><version>2.1</version><interface><name>IDemo</name><regex-instance>.*</regex-instance></interface></hal>'
        self.assertTrue(run(manifest(text))['coverage_issues'])
        self.assertTrue(run(manifest(hidl()+'<sepolicy><version>fictional</version></sepolicy>'))['coverage_issues'])

    def test_root_metadata_is_outside_instance_diff_scope(self):
        report=run(manifest(hidl()).replace('type="device"','type="device" target-level="7"'),manifest(hidl()))
        self.assertFalse(report['changes']);self.assertIn('Literal supported HAL',report['scope'])

    def test_mixed_text_is_never_silently_clean(self):
        for text in (manifest('unexpected'+hidl()),manifest(hidl().replace('<hal>','<hal>unexpected')),manifest(hidl()+'tail')):
            self.assertIn('UNINSPECTED_MIXED_TEXT',self.codes(run(text),True))

    def test_scalar_and_package_length_limits(self):
        text=manifest(hidl().replace('example.hardware.demo','example.'+'a'*257))
        self.assertIn('UNSUPPORTED_PACKAGE_NAME',self.codes(run(text),True))
        text=manifest('<x>'+'\n'.join('a'*100 for _i in range(100))+'</x>')
        with self.assertRaisesRegex(TextError,'XML_TEXT_LIMIT'):run(text)

    def test_unknown_transport_not_copied_into_fields(self):
        report=run(manifest(hidl(transport='<transport>fictional_unknown_transport</transport>')),details=True)
        self.assertIn('HIDL_TRANSPORT_NEEDS_REVIEW',self.codes(report,True))
        self.assertNotIn('fictional_unknown_transport',json.dumps(report))

    def test_actual_cli_generated_examples_and_private_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            cases=[('clean',None,0),('same','clean',0),('changed','clean',1),('review',None,1)]
            for name,before,expected in cases:
                args=[sys.executable,'-B',str(ROOT/'vintf_inspector.py'),'--file',str(base/f'fixtures/{name}.xml'),'--output',str(base/name)]
                if before:args+=['--before',str(base/f'fixtures/{before}.xml')]
                result=subprocess.run(args,capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr);self.assertNotIn(str(base),result.stdout)
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture):result=tool.main(['--file',str(base/'absent-private.xml'),'--output',str(base/'error')])
            self.assertEqual(result,2);self.assertNotIn('absent-private',capture.getvalue())


if __name__=='__main__':unittest.main()
