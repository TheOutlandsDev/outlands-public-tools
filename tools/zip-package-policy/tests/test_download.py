"""Actual PowerShell CLI from only the copied runtime file and authored inputs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PWSH=Path(os.environ['OUTLANDS_PWSH'])

class Download(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='zip-policy-cli-')
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        self.runtime=self.work/'copied runtime';self.runtime.mkdir()
        self.tool=self.runtime/'Test-ZipPackagePolicy.ps1'
        shutil.copyfile(ROOT/'Test-ZipPackagePolicy.ps1',self.tool)
        self.policy=self.work/'policy.json'
        self.policy.write_text(json.dumps(dict(schemaVersion=1)),encoding='utf-8')
        self.archive=self.work/'authored.zip'
        with zipfile.ZipFile(self.archive,'x') as target:
            target.writestr('README.txt','Fictional Orchard package.\n')
            target.writestr('settings/example.ini','[demo]\nmode=preview\n')

    def run_cli(self, archive=None, policy=None, report=None, expected=0, error=None):
        archive=archive or self.archive;policy=policy or self.policy
        before={p:p.read_bytes() for p in (archive,policy) if p.is_file()}
        args=[str(PWSH),'-NoLogo','-NoProfile','-NonInteractive','-File',str(self.tool),'-ArchivePath',str(archive),'-PolicyPath',str(policy)]
        if report is not None: args+=['-ReportPath',str(report)]
        result=subprocess.run(args,cwd=self.work,capture_output=True,text=True,encoding='utf-8',timeout=35)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        self.assertFalse(result.stderr)
        self.assertNotIn(str(self.work),result.stdout)
        for path,data in before.items(): self.assertEqual(path.read_bytes(),data)
        response=json.loads(result.stdout)
        if error: self.assertEqual(response['error'],error)
        return response

    def link(self,path,target,directory=False):
        try: path.symlink_to(target,target_is_directory=directory)
        except OSError:
            if os.name!='nt' or os.environ.get('OUTLANDS_ZIP_REQUIRE_NATIVE_LINKS')=='1': raise
            self.skipTest('Native symlink privilege unavailable')

    def test_demo_generated_with_selected_runtime_and_report_readback(self):
        demo=self.work/'demo'
        result=subprocess.run([str(PWSH),'-NoLogo','-NoProfile','-NonInteractive','-File',str(ROOT/'examples/Make-Demo.ps1'),
                               '-Destination',str(demo)],capture_output=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stderr)
        report=self.work/'fresh report.json'
        response=self.run_cli(demo/'package.zip',demo/'policy.json',report)
        self.assertEqual(response['status'],'pass')
        self.assertEqual(response,json.loads(report.read_text(encoding='utf-8')))
        data=(demo/'package.zip').read_bytes()
        self.assertEqual(response['archive']['sha256'],hashlib.sha256(data).hexdigest())
        self.assertEqual(response['archive']['bytes'],len(data))
        self.assertEqual(response['archive']['files'],2)
        self.assertNotIn('mode=preview',report.read_text())

    def test_expected_hash_and_literal_findings_are_completed_exit_one(self):
        self.policy.write_text(json.dumps(dict(schemaVersion=1,expectedSha256='0'*64,requiredMembers=['missing.txt'],
            textRules=[dict(member='README.txt',containsAll=['.*'])])),encoding='utf-8')
        response=self.run_cli(expected=1)
        self.assertEqual(response['status'],'findings')
        self.assertEqual({row['code'] for row in response['findings']},
                         {'archive_sha256_mismatch','required_member_missing','required_literal_missing'})

    def test_existing_report_and_both_input_aliases_cannot_be_overwritten(self):
        report=self.work/'existing.json';report.write_bytes(b'retained')
        for path in (report,self.archive,self.policy):
            with self.subTest(output=path.name):
                before=path.read_bytes();self.run_cli(report=path,expected=2,error='invalid_input')
                self.assertEqual(path.read_bytes(),before)

    def test_unsafe_members_collisions_and_special_metadata_are_incomplete(self):
        cases=[('traversal',[('../outside.txt',0)],'zip_unsafe_member_name'),
               ('case',[('name.txt',0),('NAME.txt',0)],'zip_duplicate_or_portable_collision'),
               ('nfc',[('caf\u00e9.txt',0),('cafe\u0301.txt',0)],'zip_duplicate_or_portable_collision'),
               ('symlink',[('link.txt',0o120777<<16)],'zip_special_member_rejected')]
        for label,entries,code in cases:
            with self.subTest(case=label):
                path=self.work/(label+'.zip');report=self.work/(label+'-report.json')
                with zipfile.ZipFile(path,'x') as target:
                    for name,attrs in entries:
                        entry=zipfile.ZipInfo(name)
                        if attrs: entry.external_attr=attrs;entry.create_system=3
                        target.writestr(entry,b'fictional')
                self.run_cli(path,report=report,expected=2,error=code)
                self.assertFalse(report.exists())

    def test_payload_is_neither_extracted_nor_executed(self):
        path=self.work/'script-payload.zip'
        with zipfile.ZipFile(path,'x') as target:
            target.writestr('nested/script.ps1',"Set-Content -LiteralPath './EXECUTED-MARKER.txt' -Value 'fictional marker'\n")
        before={p.relative_to(self.work).as_posix() for p in self.work.rglob('*')}
        response=self.run_cli(path)
        self.assertEqual(response['inspectedTextBytes'],0)
        self.assertEqual(before,{p.relative_to(self.work).as_posix() for p in self.work.rglob('*')})
        self.assertFalse((self.work/'EXECUTED-MARKER.txt').exists())

    def test_actual_symlink_input_refused(self):
        link=self.work/'input-link.zip';self.link(link,self.archive)
        self.run_cli(link,expected=2,error='linked_path_rejected')

    def test_actual_linked_output_parent_refused(self):
        target=self.work/'target';target.mkdir()
        link=self.work/'output-link';self.link(link,target,True)
        self.run_cli(report=link/'report.json',expected=2,error='linked_path_rejected')
        self.assertEqual(list(target.iterdir()),[])

    @unittest.skipUnless(os.name=='nt','Native Windows junction fixture')
    def test_actual_windows_junction_input_ancestor_refused(self):
        target=self.work/'junction target';target.mkdir();archive=target/'authored.zip'
        shutil.copyfile(self.archive,archive)
        link=self.work/'junction'
        # Fixed native command, two verified owned fixture paths, no deletion or policy changes.
        self.assertTrue(link.is_relative_to(self.work) and target.is_relative_to(self.work))
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(target)],capture_output=True,timeout=15,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stderr)
        self.run_cli(link/'authored.zip',expected=2,error='linked_path_rejected')

    def test_help_and_malformed_archive_fixed_error(self):
        result=subprocess.run([str(PWSH),'-NoLogo','-NoProfile','-NonInteractive','-File',str(self.tool),'-Help'],
                              cwd=self.work,capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0);self.assertFalse(result.stderr)
        self.assertIn('Usage:',result.stdout);self.assertNotIn(str(self.work),result.stdout)
        path=self.work/'broken.zip';path.write_bytes(b'not a ZIP')
        report=self.work/'incomplete.json'
        self.run_cli(path,report=report,expected=2,error='zip_invalid_structure')
        self.assertFalse(report.exists())

if __name__=='__main__':unittest.main()
