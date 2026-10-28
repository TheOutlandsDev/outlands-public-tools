"""Fictional contracts, OOXML, revision integrity, native I/O and real HTTP checks."""
from contextlib import closing
import copy
import http.client
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import zipfile
from xml.etree import ElementTree as E

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from documents import application as app,artifacts as a,contracts as c,journal as j,model,ooxml as x,runtime as r,web

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.example=app.example();self.template=self.example['template'];self.values=self.example['values']
    def request(self,value):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional document evidence',request=value))
    def save(self,template=None,parent=None):return app.save_template(self.request(dict(parent_id=parent,template=template or self.template)))['job']['result']
    def preview(self,template=None,values=None,sections=None):
        chosen=template or self.save();return app.preview(self.request(dict(template_id=chosen['template_id'],template_sha256=chosen['template_sha256'],values=self.values if values is None else values,sections=['summary','items'] if sections is None else sections)))['job']['result']
    def build(self,preview=None):
        chosen=preview or self.preview();return app.build(self.request(dict(preview_id=chosen['preview_id'],preview_sha256=chosen['preview_sha256'],checks=dict(quality=True,privacy=True,rights=True,context=True))))['job']['result']
    def compose(self,values=None,sections=None,template=None):return model.compose(template or self.template,self.values if values is None else values,['summary','items'] if sections is None else sections)
    def refused(self,fn,code):
        with self.assertRaisesRegex(r.WorkbenchError,'^'+code+'$'):fn()
    def reviewed(self,preview,built=None):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional private handoff',preview_id=preview['preview_id'],build_id=None if built is None else built['build_id'],checks=dict(quality=True,privacy=True,rights=True,context=True)))

class Contracts(Fixture):
    def test_exact_semantic_content_sections_and_quantity_oracle(self):
        value=self.compose();self.assertEqual(value['title'],'Service handoff for Sample instrument');self.assertEqual(value['included'],['summary','items']);self.assertEqual(value['omitted'],['notes']);self.assertEqual(value['summary'],dict(sections=2,paragraphs=2,tables=1,table_rows=2));block=value['sections'][1]['blocks'][0];self.assertEqual(block['rows'],[['Sample bracket',3],['Example cable',4]]);self.assertEqual(block['totals'],[dict(field='quantity',label='Quantity',quantity=7)])
    def test_literal_substitution_is_not_recursive_or_executable(self):
        values=dict(self.values,project='{{unknown}} <script>literal</script>');value=self.compose(values=values);self.assertEqual(value['title'],'Service handoff for '+values['project']);self.assertIn(b'&lt;script&gt;',x.parts(value)['word/document.xml'])
    def test_unknown_and_attribute_placeholder_refused(self):
        for title in ('{{unknown}}','{{project.name}}','{{project[0]}}','{{project','bad}}'):
            template=copy.deepcopy(self.template);template['title']=title;self.refused(lambda:c.template(template),'PLACEHOLDER_INVALID')
    def test_rows_cannot_be_interpolated_as_scalar_text(self):
        template=copy.deepcopy(self.template);template['title']='{{items}}';self.refused(lambda:c.template(template),'PLACEHOLDER_INVALID')
    def test_value_fields_are_exact_and_no_defaults_are_inferred(self):
        for values in (dict(self.values,extra='ignored'),{k:v for k,v in self.values.items() if k!='summary'}):self.refused(lambda:self.compose(values=values),'FIELDS_INVALID')
    def test_quantity_is_nonnegative_bounded_integer_not_boolean(self):
        for number in (True,-1,1.5,'3',1000000000):
            values=copy.deepcopy(self.values);values['items'][0]['quantity']=number;self.refused(lambda:self.compose(values=values),'INTEGER_INVALID')
    def test_row_fields_are_exact(self):
        values=copy.deepcopy(self.values);values['items'][0]['extra']='not accepted';self.refused(lambda:self.compose(values=values),'FIELDS_INVALID')
    def test_empty_table_is_explicit_zero_quantity(self):
        values=dict(self.values,items=[]);value=self.compose(values=values);self.assertEqual(value['summary']['table_rows'],0);self.assertEqual(value['sections'][1]['blocks'][0]['totals'][0]['quantity'],0)
    def test_required_optional_and_unknown_selection_rules(self):
        for selected in (['items'],['summary','missing'],['summary','summary']):
            with self.assertRaises(r.WorkbenchError):self.compose(sections=selected)
        self.assertEqual(self.compose(sections=['summary'])['summary']['tables'],0)
    def test_template_order_wins_over_request_selection_order(self):self.assertEqual(self.compose(sections=['items','summary'])['included'],['summary','items'])
    def test_mapping_and_section_names_unique_ignoring_case(self):
        for field in ('fields','sections'):
            template=copy.deepcopy(self.template);row=copy.deepcopy(template[field][0]);row['name' if field=='fields' else 'id']=row['name' if field=='fields' else 'id'].upper();template[field].append(row)
            self.refused(lambda:c.template(template),'NAME_DUPLICATE')
    def test_table_width_and_total_contracts_refused(self):
        template=copy.deepcopy(self.template);template['sections'][1]['blocks'][0]['columns'][0]['width']=70;self.refused(lambda:c.template(template),'TABLE_WIDTHS_INVALID');template=copy.deepcopy(self.template);template['sections'][1]['blocks'][0]['totals']=['item'];self.refused(lambda:c.template(template),'TABLE_TOTAL_INVALID')
    def test_table_source_must_be_declared_rows(self):
        template=copy.deepcopy(self.template);template['sections'][1]['blocks'][0]['source']='project';self.refused(lambda:c.template(template),'TABLE_SOURCE_INVALID')
    def test_normalized_line_endings_are_visible_in_preview(self):
        values=dict(self.values,summary='First\r\nSecond\rThird');self.assertEqual(self.compose(values=values)['sections'][0]['blocks'][0]['text'],'First\nSecond\nThird')
    def test_control_surrogate_and_text_bounds_refused(self):
        for text in ('bad\x01value','\ufffe','\ud800','x'*801):
            with self.assertRaises(r.WorkbenchError):self.compose(values=dict(self.values,summary=text))
    def test_template_values_and_preview_size_caps(self):
        with mock.patch.object(c,'MAX_TEMPLATE',1):self.refused(lambda:c.template(self.template),'TEMPLATE_LIMIT')
        with mock.patch.object(c,'MAX_VALUES',1):self.refused(lambda:self.compose(),'VALUES_LIMIT')
        with mock.patch.object(c,'MAX_PREVIEW',1):self.refused(lambda:self.compose(),'PREVIEW_LIMIT')
    def test_row_cap_refused(self):
        values=dict(self.values,items=[self.values['items'][0]]*101);self.refused(lambda:self.compose(values=values),'LIST_LIMIT')
    def test_request_json_duplicate_depth_and_nonfinite_refused(self):
        for raw in (b'{"a":1,"a":2}',b'['*70+b'0'+b']'*70,b'{"n":NaN}'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)
    def test_selectors_reject_parent_device_stream_and_alias_syntax(self):
        for value in ('../outside','inbox/../outside','inbox/NUL.txt','inbox/end.','inbox/name:stream','inbox//file','inbox/dir\\file'):
            with self.assertRaises(r.WorkbenchError):c.selector(value)

class XmlPackage(Fixture):
    def test_package_detection_parts_use_conventional_default_namespaces(self):
        parts=x.parts(self.compose())
        for name,namespace in [('[Content_Types].xml',x.CT),('_rels/.rels',x.REL),('word/_rels/document.xml.rels',x.REL),('docProps/app.xml',x.APP)]:
            self.assertIn(('xmlns="'+namespace+'"').encode(),parts[name]);self.assertNotIn(b'<ns0:',parts[name]);E.fromstring(parts[name])
    def test_eight_exact_parts_and_independent_word_text_oracle(self):
        value=self.compose();raw=x.build(value);inspection=x.inspect(raw,value);self.assertEqual(inspection['parts'],8);self.assertEqual(inspection['external_relationships'],0)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(set(z.namelist()),{'[Content_Types].xml','_rels/.rels','docProps/core.xml','docProps/app.xml','word/document.xml','word/styles.xml','word/settings.xml','word/_rels/document.xml.rels'});doc=E.fromstring(z.read('word/document.xml'));texts=[node.text for node in doc.iter(x.tag('t'))];self.assertIn('Service handoff for Sample instrument',texts);self.assertIn('Sample bracket',texts);self.assertIn('Example cable',texts);self.assertIn('Total quantity 7',texts);self.assertNotIn('Review notes',texts)
    def test_fixed_neutral_properties_zip_metadata_and_no_default_template_parts(self):
        raw=x.build(self.compose())
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            core=E.fromstring(z.read('docProps/core.xml'));self.assertEqual(core.find('{'+x.DC+'}creator').text,'OUTLANDS');self.assertEqual(core.find('{'+x.CP+'}lastModifiedBy').text,'OUTLANDS');self.assertEqual(core.find('{'+x.DC+'}title').text,'Generated document');self.assertNotIn(b'Sample instrument',z.read('docProps/core.xml'))
            for item in z.infolist():self.assertEqual(item.date_time,(2020,1,1,0,0,0));self.assertFalse(item.extra or item.comment)
            self.assertFalse(any('thumbnail' in name or 'customXml' in name for name in z.namelist()))
    def test_repeat_builds_have_identical_bytes(self):self.assertEqual(x.build(self.compose()),x.build(self.compose()))
    def test_letter_margins_repeated_header_widths_borders_and_black_titles(self):
        parts=x.parts(self.compose());doc=E.fromstring(parts['word/document.xml']);page=doc.find('.//'+x.tag('pgSz'));self.assertEqual((page.get(x.tag('w')),page.get(x.tag('h'))),('12240','15840'));self.assertEqual(len(doc.findall('.//'+x.tag('tblHeader'))),1);widths=[int(node.get(x.tag('w'))) for node in doc.findall('.//'+x.tag('gridCol'))];self.assertEqual(widths,[7020,2340]);self.assertEqual(sum(widths),9360);self.assertTrue(all(node.get(x.tag('color'))=='D9D9D9' for node in doc.findall('.//'+x.tag('tblBorders')+'/*')));styles=E.fromstring(parts['word/styles.xml']);self.assertTrue(all(node.get(x.tag('val'))=='000000' for node in styles.findall('.//'+x.tag('color'))))
    def test_extra_part_and_external_relationship_refused(self):
        value=self.compose();parts=x.parts(value);parts['word/media/private.bin']=b'fictional';buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            for name,raw in parts.items():z.writestr(name,raw)
        self.refused(lambda:x.inspect(buffer.getvalue(),value),'DOCX_PARTS_REFUSED')
        parts=x.parts(value);parts['word/_rels/document.xml.rels']=parts['word/_rels/document.xml.rels'].replace(b'styles.xml',b'https://example.invalid/template');buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            for name,raw in parts.items():info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;z.writestr(info,raw)
        self.refused(lambda:x.inspect(buffer.getvalue(),value),'DOCX_CONTENT_MISMATCH')
    def test_zip_comment_refused_as_unreviewed_metadata(self):
        value=self.compose();buffer=io.BytesIO(x.build(value))
        with zipfile.ZipFile(buffer,'a') as z:z.comment=b'fictional unapproved comment'
        self.refused(lambda:x.inspect(buffer.getvalue(),value),'DOCX_METADATA_REFUSED')
    def test_xml_markup_is_literal_without_fields_or_embedded_objects(self):
        value=self.compose(values=dict(self.values,summary='<script>literal</script> & text'));parts=x.parts(value);doc=E.fromstring(parts['word/document.xml']);self.assertIn('<script>literal</script> & text',[node.text for node in doc.iter(x.tag('t'))]);self.assertFalse(doc.findall('.//'+x.tag('fldSimple')) or doc.findall('.//'+x.tag('object')))
    def test_multiline_and_tab_text_use_word_break_elements(self):
        parts=x.parts(self.compose(values=dict(self.values,summary='First\nSecond\tThird')));doc=E.fromstring(parts['word/document.xml']);self.assertEqual(len(doc.findall('.//'+x.tag('br'))),1);self.assertEqual(len(doc.findall('.//'+x.tag('tab'))),1)
    def test_size_cap_and_invalid_package_refused(self):
        with mock.patch.object(c,'MAX_DOCX',1):self.refused(lambda:x.build(self.compose()),'DOCX_SIZE_LIMIT')
        self.refused(lambda:x.inspect(b'not a package',self.compose()),'DOCX_PACKAGE_INVALID')

class Workflows(Fixture):
    def test_complete_demo_independent_counts(self):
        before={p.name:p.read_bytes() for p in (self.root/'inbox').iterdir()};value=app.demo();self.assertEqual((value['templates'],value['previews'],value['builds'],value['journal_events']),(2,2,2,12));self.assertEqual(value['total_quantity'],7);self.assertEqual(value['changed_sections'],['items']);self.assertEqual(value['private_report_files'],9);self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'inbox').iterdir()})
    def test_immutable_revision_parent_and_detailed_comparison(self):
        first=self.save();raw=(self.root/first['target']/'template.json').read_bytes();edited=copy.deepcopy(self.template);edited['sections'][1]['title']='Revised quantities';second=self.save(edited,first['template_id']);comparison=app.compare(first['template_id'],second['template_id']);self.assertEqual(comparison['sections']['changed'],['items']);self.assertFalse(comparison['same_template_bytes']);self.assertEqual(second['parent_id'],first['template_id']);self.assertEqual((self.root/first['target']/'template.json').read_bytes(),raw)
    def test_historical_preview_survives_new_template_revision(self):
        first=self.save();preview=self.preview(first);raw=(self.root/preview['target']/'preview.json').read_bytes();edited=copy.deepcopy(self.template);edited['title']='Different title';self.save(edited,first['template_id']);built=self.build(preview);self.assertEqual(app.inspect_build(built['build_id'])['preview']['title'],'Service handoff for Sample instrument');self.assertEqual((self.root/preview['target']/'preview.json').read_bytes(),raw)
    def test_review_and_pin_required_before_build_job(self):
        preview=self.preview();request=dict(preview_id=preview['preview_id'],preview_sha256=preview['preview_sha256'],checks=dict(quality=True,privacy=False,rights=True,context=True));self.refused(lambda:app.build(self.request(request)),'REVIEW_REQUIRED');request['checks']['privacy']=True;request['preview_sha256']='1'*64;self.refused(lambda:app.build(self.request(request)),'PREVIEW_NOT_REGISTERED_OR_PIN_MISMATCH');self.assertEqual(len(app.overview()['jobs']),2)
    def test_bool_review_value_is_not_integer_truthiness(self):
        preview=self.preview();request=dict(preview_id=preview['preview_id'],preview_sha256=preview['preview_sha256'],checks=dict(quality=1,privacy=True,rights=True,context=True));self.refused(lambda:app.build(self.request(request)),'REVIEW_REQUIRED')
    def test_unknown_parent_or_template_pin_does_not_create_artifacts(self):
        self.refused(lambda:self.save(parent='1'*32),'PARENT_NOT_REGISTERED');first=self.save();bad=dict(first,template_sha256='1'*64);self.refused(lambda:self.preview(bad),'TEMPLATE_NOT_REGISTERED_OR_PIN_MISMATCH');self.assertEqual(list((self.root/'previews').iterdir()),[])
    def test_stale_head_refused(self):
        raw=self.request(dict(parent_id=None,template=self.template));self.save();self.refused(lambda:app.save_template(raw),'JOURNAL_HEAD_CONFLICT');self.assertEqual(len(app.overview()['templates']),1)
    def test_two_competing_requests_accept_only_one(self):
        raw=self.request(dict(parent_id=None,template=self.template));results=[]
        def run():
            try:app.save_template(raw);results.append('ok')
            except r.WorkbenchError as error:results.append(str(error))
        threads=[threading.Thread(target=run) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=15);self.assertFalse(thread.is_alive())
        self.assertCountEqual(results,['ok','JOURNAL_HEAD_CONFLICT'])
    def test_fresh_builds_identical_bytes_without_replacing_prior_document(self):
        preview=self.preview();first=self.build(preview);raw=(self.root/first['target']/'document.docx').read_bytes();second=self.build(preview);self.assertNotEqual(first['target'],second['target']);self.assertEqual(raw,(self.root/second['target']/'document.docx').read_bytes());self.assertEqual(app.document_bytes(first['build_id']),raw)
    def test_template_artifact_and_marker_tampering_refused(self):
        first=self.save();(self.root/first['target']/'template.json').write_bytes(b'{}');self.refused(lambda:app.inspect_template(first['template_id']),'TEMPLATE_HASH_MISMATCH')
    def test_preview_artifact_tampering_records_build_failure(self):
        preview=self.preview();(self.root/preview['target']/'preview.json').write_bytes(b'{}');self.refused(lambda:self.build(preview),'PREVIEW_HASH_MISMATCH');self.assertEqual(app.overview()['jobs'][-1]['status'],'failed');self.assertEqual(app.overview()['builds'],[])
    def test_marker_tampering_visible(self):
        preview=self.preview();(self.root/preview['target']/'READY.json').write_bytes(b'{}');self.refused(lambda:app.inspect_preview(preview['preview_id']),'PREVIEW_MARKER_MISMATCH')
    def test_document_and_retained_preview_tampering_refused(self):
        preview=self.preview();built=self.build(preview);(self.root/built['target']/'document.docx').write_bytes(b'fictional corruption');self.refused(lambda:app.document_bytes(built['build_id']),'DOCUMENT_HASH_MISMATCH')
    def test_build_preview_and_marker_are_exact(self):
        preview=self.preview();built=self.build(preview);(self.root/built['target']/'preview.json').write_bytes(b'{}');self.refused(lambda:app.inspect_build(built['build_id']),'BUILD_PREVIEW_MISMATCH')
    def test_partial_failure_retains_output_and_generic_error(self):
        preview=self.preview()
        def partial(identifier,request,state):
            directory=self.root/'builds'/identifier;r.mkdir(directory);r.write_new(directory/'document.docx',b'fictional partial');raise OSError('withheld detail')
        with mock.patch.object(a,'write_build',partial):self.refused(lambda:self.build(preview),'OPERATION_REFUSED')
        job=app.overview()['jobs'][-1];self.assertEqual(job['error'],'OPERATION_REFUSED');self.assertTrue((self.root/'builds'/job['job_id']/'document.docx').is_file());self.assertEqual(app.overview()['builds'],[])
    def test_orphan_built_marker_not_adopted_and_recovery_does_not_replay(self):
        preview=self.preview();original=j.append
        def interrupted(event,head):
            if event['operation']=='job_completed':raise KeyboardInterrupt
            return original(event,head)
        with mock.patch.object(j,'append',interrupted):
            with self.assertRaises(KeyboardInterrupt):self.build(preview)
        state=app.overview();identifier=state['jobs'][-1]['job_id'];self.assertTrue((self.root/'builds'/identifier/'BUILT.json').is_file());self.refused(lambda:app.inspect_build(identifier),'BUILD_NOT_REGISTERED');self.refused(lambda:self.save(),'UNFINISHED_JOB_REVIEW_REQUIRED');app.recover(r.encode(dict(actor='sample_recovery',reason='Fictional stopped review')));self.assertEqual(app.overview()['jobs'][-1]['status'],'interrupted');self.assertEqual(app.overview()['builds'],[]);self.assertTrue((self.root/'builds'/identifier/'BUILT.json').is_file())
    def test_uncertain_completed_response_keeps_registered_build(self):
        preview=self.preview();original=j.append
        def uncertain(event,head):
            value=original(event,head)
            if event['operation']=='job_completed':raise OSError('lost response')
            return value
        with mock.patch.object(j,'append',uncertain):self.refused(lambda:self.build(preview),'OPERATION_REFUSED')
        state=app.overview();self.assertEqual(len(state['builds']),1);self.assertTrue(app.inspect_build(state['builds'][0]['build_id'])['inspection']['model_matched'])
    def test_existing_output_directory_is_not_reused(self):
        identifier='1'*32;directory=self.root/'templates'/identifier;directory.mkdir();(directory/'sentinel').write_bytes(b'keep')
        with mock.patch.object(app.uuid,'uuid4',return_value=mock.Mock(hex=identifier)):self.refused(self.save,'FILESYSTEM_REFUSED')
        self.assertEqual((directory/'sentinel').read_bytes(),b'keep')
    def test_index_schema_and_append_only_trigger_protections(self):
        self.save()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            with self.assertRaisesRegex(sqlite3.IntegrityError,'append only'):con.execute('DELETE FROM events')
            con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        self.refused(app.overview,'STORE_SCHEMA_REFUSED')
    def test_offline_hash_tampering_refused(self):
        self.save()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');con.execute('UPDATE events SET sha256=? WHERE sequence=1',('f'*64,));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_HASH_MISMATCH')
    def test_rehashed_typed_count_tampering_refused(self):
        self.preview()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');value=r.decode(con.execute('SELECT payload_json FROM events WHERE sequence=4').fetchone()[0].encode());value['event']['data']['result']['summary']['tables']=True;raw=r.encode(value);con.execute('UPDATE events SET sha256=?,payload_json=? WHERE sequence=4',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_RESULT_INVALID')
    def test_event_cap_reserves_terminal_slot(self):
        with mock.patch.object(c,'MAX_EVENTS',2):self.save();self.assertEqual(app.overview()['sequence'],2);self.refused(self.save,'JOURNAL_LIMIT')
    def test_reviewed_handoff_has_document_values_hashes_and_no_public_permission(self):
        preview=self.preview();built=self.build(preview);out=app.export(self.reviewed(preview,built));directory=self.root/out['directory'];manifest=out['manifest'];self.assertTrue(manifest['contains_document'] and manifest['contains_input_values']);self.assertFalse(manifest['public_release_authorized']);self.assertEqual(len(list(directory.iterdir())),9);self.assertEqual((directory/'document.docx').read_bytes(),app.document_bytes(built['build_id']))
        for name,item in manifest['files'].items():raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=r.digest(raw)))
    def test_export_review_and_mismatched_build_refused(self):
        first=self.preview();built=self.build(first);value=r.decode(self.reviewed(first,built));value['checks']['privacy']=False;self.refused(lambda:app.export(r.encode(value)),'REVIEW_REQUIRED');second=self.preview();self.refused(lambda:app.export(self.reviewed(second,built)),'BUILD_PREVIEW_MISMATCH')
    def test_private_index_backup_contains_values_but_not_document_files(self):
        self.preview();out=app.backup_index();self.assertTrue(out['contains_input_values']);self.assertFalse(out['includes_document_files']);self.assertEqual(r.digest((self.root/out['file']).read_bytes()),out['sha256'])
        with closing(sqlite3.connect(self.root/out['file'])) as con:self.assertEqual(j.load(con)[0]['sequence'],4)
    def test_instance_inside_source_and_existing_outputs_refused(self):
        with self.assertRaises(r.WorkbenchError):r.write_new(self.root/'inbox/template.json',b'no overwrite')
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP/'private-instance',create=True)
        self.assertFalse((APP/'private-instance').exists())
    def test_stale_session_and_cli_outside_request_refused(self):
        r.close();(self.root/'.session-lock').mkdir();self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);r.close();p=subprocess.run([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'save-template','--file','../outside.json'],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout),dict(error='SELECTOR_INVALID'));self.assertNotIn(str(self.root),p.stdout)
    def test_actual_child_interruption_retains_partial_and_requires_recovery(self):
        r.close();program='''import sys,threading\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom documents import application as app,artifacts as a,runtime as r\nr.configure(sys.argv[2])\ndef stopped(identifier,request):\n p=r.ROOT/'templates'/identifier;r.mkdir(p);r.write_new(p/'PARTIAL.txt',b'fictional interrupted revision');r.write_new(r.ROOT/'owned-child-ready',b'ready');threading.Event().wait(120)\na.write_template=stopped\napp.save_template(r.encode(dict(expected_head=app.overview()['head'],actor='sample_child',reason='Controlled interruption',request=dict(parent_id=None,template=app.example()['template']))))\n''';p=subprocess.Popen([sys.executable,'-B','-W','error','-c',program,str(APP),str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+20
            while not (self.root/'owned-child-ready').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue((self.root/'owned-child-ready').exists());p.kill();p.communicate(timeout=10);self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);self.assertEqual(app.overview()['unfinished_jobs'],1);app.recover(r.encode(dict(actor='sample_recovery',reason='Owned child stopped')));state=app.overview();self.assertEqual(state['jobs'][0]['status'],'interrupted');self.assertEqual(state['templates'],[]);self.assertTrue((self.root/'templates'/state['jobs'][0]['job_id']/'PARTIAL.txt').is_file());self.assertEqual((self.root/'inbox/template.json').read_bytes(),(APP/'examples/template.json').read_bytes())
        finally:
            if p.poll() is None:p.kill()
            p.communicate(timeout=10)

class NativeBoundaries(Fixture):
    def make_link(self,action):
        try:action()
        except (OSError,subprocess.SubprocessError):
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('NATIVE_FIXTURE_REQUIRED')
            self.skipTest('Native link creation unavailable on this test filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias.json';self.make_link(lambda:os.link(self.root/'inbox/template.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias'))
        with self.assertRaises(r.WorkbenchError):app.overview()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias.json';self.make_link(lambda:os.symlink(self.root/'inbox/template.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'template.json')
    def test_native_template_hardlink_refused(self):
        template=self.save();self.make_link(lambda:os.link(self.root/template['target']/'template.json',self.root/'inbox/template-alias.json'))
        with self.assertRaises(r.WorkbenchError):app.inspect_template(template['template_id'])
    def test_native_document_hardlink_refused(self):
        built=self.build();self.make_link(lambda:os.link(self.root/built['target']/'document.docx',self.root/'inbox/document-alias'))
        with self.assertRaises(r.WorkbenchError):app.document_bytes(built['build_id'])
    def test_native_junction_or_directory_link_output_parent_refused(self):
        path=self.root/'builds';path.rmdir();target=self.root/'controlled-target';target.mkdir()
        if os.name=='nt':
            script=self.root/'inbox/junction-fixture.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\n$ErrorActionPreference="Stop"\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null\n',encoding='utf-8');self.make_link(lambda:subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),str(path),str(target)],capture_output=True,check=True));self.addCleanup(lambda:os.rmdir(path))
        else:self.make_link(lambda:os.symlink(target,path,target_is_directory=True))
        preview=self.preview()
        with self.assertRaises(r.WorkbenchError):self.build(preview)
        self.assertEqual(list(target.iterdir()),[])
    @unittest.skipUnless(os.name!='nt','POSIX-only FIFO boundary')
    def test_posix_fifo_input_refused_without_blocking(self):
        path=self.root/'inbox/pipe';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream selector boundary')
    def test_windows_stream_selector_refused(self):self.refused(lambda:c.selector('inbox/template.json:stream'),'SELECTOR_INVALID')

class HttpBoundaries(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def http(self,path,method='GET',body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:con.request(method,path,body=body,headers=headers or {});res=con.getresponse();return res.status,res.read(),dict(res.getheaders())
        finally:con.close()
    def test_root_security_headers_and_no_html_injection_api(self):
        status,raw,headers=self.http('/');self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('frame-ancestors',headers['Content-Security-Policy']);self.assertNotIn(b'innerHTML',raw)
    def test_host_token_and_origin_refused(self):
        self.assertEqual(self.http('/api/overview')[0],403);self.assertEqual(self.http('/',headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.http('/api/template','POST',self.request(dict(parent_id=None,template=self.template)),{'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403)
    def test_duplicate_query_and_body_keys_refused(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.http('/api/job?id=a&id=b',headers=headers)[0],400);self.assertEqual(self.http('/api/template','POST',b'{"a":1,"a":2}',headers)[0],400)
    def test_actual_http_revision_and_template_details(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.http('/api/template','POST',self.request(dict(parent_id=None,template=self.template)),headers);self.assertEqual(status,200);identifier=json.loads(raw)['job']['result']['template_id'];status,raw,_=self.http('/api/template?id='+identifier,headers=headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['template'],self.template)
    def test_verified_document_download_has_static_filename_and_exact_bytes(self):
        built=self.build();status,raw,headers=self.http('/api/document?id='+built['build_id'],headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(status,200);self.assertEqual(raw,app.document_bytes(built['build_id']));self.assertEqual(headers['Content-Disposition'],'attachment; filename="generated-document.docx"');self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(self.http('/api/document?id='+built['build_id'])[0],403)

if __name__=='__main__':unittest.main()
