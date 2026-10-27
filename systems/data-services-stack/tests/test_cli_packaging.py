from base import APP, Fixture, fictional_configuration, fictional_input
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from unittest import mock
import zipfile

from data_services.cli import demo
from data_services.contracts import StackError, digest
from data_services.packaging import package, source_check, source_files
from data_services.service import Stack


class CliPackaging(Fixture):
    def call(self,*arguments,expected=0,app=APP):
        result = subprocess.run([sys.executable,"-B",str(app/"stack.py"),*map(str,arguments)],
                                cwd=self.parent,capture_output=True,text=True,timeout=45)
        self.assertEqual((result.returncode,result.stderr),(expected,""))
        return result.stdout

    def test_actual_cli_configure_run_reopen_dispatch_report_and_export(self):
        self.call("--workspace",self.root,"init")
        self.call("--workspace",self.root,"configure","--config",APP/"examples/jobs.json")
        self.call("--workspace",self.root,"run","--job","sample","--key","notice","--input",APP/"examples/sample.jsonl")
        self.assertEqual(json.loads(self.call("--workspace",self.root,"dispatch-fake","--now",0,"--outcomes","retry"))[0]["next_attempt"],1)
        self.assertEqual(json.loads(self.call("--workspace",self.root,"dispatch-fake","--now",1))[0]["attempts"],2)
        self.call("--workspace",self.root,"report-delivery","--key","notice","--receipt","fake_receipt")
        output = self.parent/"result.json"
        self.call("--workspace",self.root,"export","--key","notice","--output",output)
        self.assertEqual(json.loads(output.read_bytes())["state"],"COMPLETED")
        before = output.read_bytes()
        self.call("--workspace",self.root,"export","--key","notice","--output",output,expected=2)
        self.assertEqual(output.read_bytes(),before)

    def test_actual_demo_is_persistent_fictional_and_without_replay(self):
        result = json.loads(self.call("--workspace",self.root,"demo"))
        self.assertEqual(result["mode"],"FICTIONAL_DATA_SERVICES_DEMO")
        self.assertFalse(result["real_delivery_verified"])
        self.assertEqual(result["replay_after_restart"],[])
        with Stack(self.root) as app:
            self.assertEqual([q["state"] for q in app.queue()],["DELIVERY_REPORTED","REVIEW_REQUIRED"])

    def test_demo_has_no_network_shell_or_external_process_adapter(self):
        with mock.patch.object(socket,"socket",side_effect=AssertionError("NETWORK")), mock.patch.object(os,"system",side_effect=AssertionError("SHELL")), mock.patch.object(subprocess,"run",side_effect=AssertionError("PROCESS")):
            result = demo(self.root)
        self.assertEqual(result["result"]["score"],dict(count=3,mae=4,rmse=4))

    def test_bad_arguments_and_selected_paths_are_not_echoed(self):
        raw = self.call("--unknown","FICTIONAL_DO_NOT_ECHO",expected=2)
        self.assertEqual(json.loads(raw),dict(status="ERROR",code="ARGUMENTS_INVALID"))
        raw = self.call("--workspace",self.parent/"FICTIONAL_DO_NOT_ECHO","status",expected=2)
        self.assertNotIn("FICTIONAL_DO_NOT_ECHO",raw)
        self.assertNotIn(str(self.parent),raw)

    def test_rejected_run_exit_code_and_no_notification(self):
        self.create()
        source = self.parent/"bad.jsonl"
        source.write_bytes(b"null")
        result = json.loads(self.call("--workspace",self.root,"run","--job","sample","--key","bad","--input",source,expected=2))
        self.assertEqual(result["state"],"REJECTED")
        self.assertEqual(json.loads(self.call("--workspace",self.root,"status"))["queue"],[])

    def test_help_is_static_and_does_not_contain_source_path(self):
        raw = self.call("--help")
        self.assertIn("data-services",raw)
        self.assertNotIn(str(APP),raw)

    def test_recovery_requires_confirmation_before_removing_stale_lock(self):
        self.create()
        lock = self.root/".writer-lock"
        lock.mkdir()
        self.call("--workspace",self.root,"recover",expected=2)
        self.assertTrue(lock.is_dir())
        self.call("--workspace",self.root,"recover","--confirm-stopped")
        self.assertFalse(lock.exists())

    def test_source_manifest_verifies_exact_selected_bytes(self):
        result = source_check()
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["files"],len(source_files()))
        self.assertEqual(json.loads(self.call("source-check")),result)

    def test_source_zip_is_deterministic_and_contains_only_manifest_members(self):
        one,two = self.parent/"one.zip",self.parent/"two.zip"
        first,second = package(one),package(two)
        self.assertEqual(first,second)
        self.assertEqual(one.read_bytes(),two.read_bytes())
        self.assertEqual(first["sha256"],digest(one.read_bytes()))
        with zipfile.ZipFile(one) as archive:
            self.assertEqual(set(archive.namelist()),{"data-services-stack/"+p for p in source_files()})
            for info in archive.infolist():
                self.assertEqual(info.date_time,(1980,1,1,0,0,0))
                self.assertEqual(info.create_system,3)
                self.assertEqual(info.external_attr>>16,0o100644)
                self.assertNotIn("..",Path(info.filename).parts)

    def test_source_zip_existing_or_source_tree_output_is_refused(self):
        target = self.parent/"source.zip"
        target.write_bytes(b"Fictional retained output.")
        with self.assertRaises(StackError):package(target)
        self.assertEqual(target.read_bytes(),b"Fictional retained output.")
        forbidden = APP/"fictional-forbidden.zip"
        with self.assertRaises(StackError):package(forbidden)
        self.assertFalse(forbidden.exists())

    def test_extracted_source_runs_and_verifies_without_collection(self):
        archive_path = self.parent/"source.zip"
        package(archive_path)
        extracted = self.parent/"extracted"
        extracted.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            expected = {"data-services-stack/"+p for p in source_files()}
            self.assertEqual(set(archive.namelist()),expected)
            archive.extractall(extracted)
        standalone = extracted/"data-services-stack"
        self.assertEqual(json.loads(self.call("source-check",app=standalone))["status"],"PASS")
        result = json.loads(self.call("--workspace",self.parent/"standalone-state","demo",app=standalone))
        self.assertFalse(result["real_delivery_verified"])

    def test_public_component_snapshots_keep_reviewed_algorithms(self):
        expected = {
            "components/ingestion.py":"d687e10ea4abb2c6cc35c63294df48ebcc6889b37658217f54e09c95e36b7c4b",
            "components/evaluator.py":"9d0acd6979c01fff64f346dd45926280537b773da4c4a549f7f5b24c294fe224",
            "components/outbox.py":"d38e7c86fe53dda5da7df12aebfaf4525726f00c2f234b78548c2ee678716f78"}
        for name,sha in expected.items():
            raw = (APP/"data_services"/name).read_bytes()
            if name.endswith("evaluator.py"):
                raw = raw.replace(b"from .ingestion import ",b"from ingestion import ",1)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)
