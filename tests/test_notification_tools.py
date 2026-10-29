"""Actual fictional independent CLIs and public-outbox semantic interoperability."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'message-template-renderer':'render.py','message-envelope-checker':'envelope.py',
       'eml-mime-inspector':'inspect_eml.py','delivery-evidence-reconciler':'delivery.py'}


class Walkthrough(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fictional-notification-tools-')
        self.addCleanup(temp.cleanup); self.private=Path(temp.name)

    def call(self,root,script,args,code=0):
        result=subprocess.run([sys.executable,'-B',str(root/script),*args],cwd=self.private,
                              capture_output=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout.decode('utf-8',errors='replace'))
        self.assertEqual(result.stderr,b''); return json.loads(result.stdout)

    def args(self,name,root):
        if name=='message-template-renderer':
            return ['--template',str(root/'examples/template.json'),'--values',str(root/'examples/values.json')]
        if name=='eml-mime-inspector':
            selected=self.private/'fictional.eml'
            if not selected.exists(): self.call(root,'fictional_eml.py',['--out',str(selected)])
            return ['--input',str(selected)]
        return ['--input',str(root/('examples/envelope.json' if name=='message-envelope-checker' else 'examples/evidence.json'))]

    def test_all_fictional_cli_examples(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name
            with self.subTest(tool=name): self.assertEqual(self.call(root,script,self.args(name,root))['status'],'PASS')

    def test_all_standalone_copied_source_and_pins(self):
        for name,script in TOOLS.items():
            root=self.private/name
            shutil.copytree(ROOT/'tools'/name,root,ignore=shutil.ignore_patterns('__pycache__'))
            with self.subTest(tool=name):
                self.call(root,script,self.args(name,root))
                self.assertEqual(self.call(root,'source_check.py',[])['status'],'SOURCE_MATCH')

    def test_new_reports_and_overwrite_refusal(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; target=self.private/(name+'.json')
            args=self.args(name,root)+['--out',str(target)]
            self.assertTrue(self.call(root,script,args)['report_written']); original=target.read_bytes()
            self.assertEqual(self.call(root,script,args,2)['status'],'ERROR'); self.assertEqual(target.read_bytes(),original)

    def test_argument_errors_do_not_echo_values(self):
        for name,script in TOOLS.items():
            self.assertEqual(self.call(ROOT/'tools'/name,script,['--unknown','FICTIONAL_SENTINEL'],2),dict(status='ERROR',code='ARGUMENTS_INVALID'))

    def test_uncertain_cli_exit_and_retained_review(self):
        root=ROOT/'tools/delivery-evidence-reconciler'
        result=self.call(root,'delivery.py',['--input',str(root/'examples/uncertain.json')],1)
        self.assertEqual(result['messages'][0]['state'],'REVIEW_REQUIRED'); self.assertFalse(result['real_delivery_verified'])

    def test_fictional_generator_is_new_file_only(self):
        root=ROOT/'tools/eml-mime-inspector'; target=self.private/'sample.eml'
        self.call(root,'fictional_eml.py',['--out',str(target)]); original=target.read_bytes()
        self.call(root,'fictional_eml.py',['--out',str(target)],2); self.assertEqual(target.read_bytes(),original)

    def test_public_outbox_acceptance_and_uncertainty_agree(self):
        # Public fake transport executes here. Its states are converted to explicit invented evidence.
        program="""
import json,sys
sys.path.insert(0,sys.argv[1])
from outbox import Outbox, Message, FakeTransport
result=[]
for script in [('retry','accept'),('accepted_then_unknown',)]:
    box=Outbox(max_attempts=3)
    box.enqueue(Message('sample','sample_route','Fictional','Invented body'))
    fake=FakeTransport(outcomes=script)
    first=box.dispatch(fake,now=0)[0]
    second=box.dispatch(fake,now=1)
    result.append(dict(first=first.state,last=box.snapshot('sample').state,calls=fake.calls))
print(json.dumps(result))
"""
        result=subprocess.run([sys.executable,'-B','-c',program,str(ROOT/'tools/notification-outbox')],cwd=self.private,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        actual=json.loads(result.stdout)
        self.assertEqual(actual[0]['first'],'PENDING'); self.assertEqual(actual[0]['last'],'ACCEPTED')
        self.assertEqual(actual[1]['last'],'REVIEW_REQUIRED'); self.assertEqual(actual[1]['calls'],1)
        root=ROOT/'tools/delivery-evidence-reconciler'
        accepted=self.call(root,'delivery.py',['--input',str(root/'examples/evidence.json')])
        unknown=self.call(root,'delivery.py',['--input',str(root/'examples/uncertain.json')],1)
        self.assertEqual(accepted['messages'][0]['attempts'],2)
        self.assertEqual(unknown['messages'][0]['state'],actual[1]['last'])

    def test_render_and_envelope_keep_body_and_headers_separate(self):
        root=ROOT/'tools/message-template-renderer'
        result=self.call(root,'render.py',self.args('message-template-renderer',root))
        self.assertIn('\nUnits: 7',result['text'])
        envelope=ROOT/'tools/message-envelope-checker'
        selected=self.private/'envelope.json'
        value=json.loads((envelope/'examples/envelope.json').read_text(encoding='utf-8'))
        value['subject']=result['text']; selected.write_text(json.dumps(value),encoding='utf-8')
        rejected=self.call(envelope,'envelope.py',['--input',str(selected)],2)
        self.assertEqual(rejected['code'],'TEXT_CONTROL_FORBIDDEN')
