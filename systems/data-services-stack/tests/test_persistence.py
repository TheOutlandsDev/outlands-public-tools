from base import APP, Fixture, fictional_configuration, fictional_input
from copy import deepcopy
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
from unittest import mock

from data_services import files
from data_services.components.outbox import FakeTransport
from data_services.contracts import StackError
from data_services.service import Stack
import data_services.journal as journal


class Persistence(Fixture):
    def test_init_is_new_directory_only_and_never_replaces_existing_state(self):
        self.create(run=True)
        before = self.hashes()
        with self.assertRaises(StackError):
            Stack.initialize(self.root)
        self.assertEqual(self.hashes(),before)

    def test_source_checkout_is_refused_as_private_output(self):
        destination = APP/"fictional-forbidden-state"
        with self.assertRaises(StackError):
            Stack.initialize(destination)
        self.assertFalse(destination.exists())

    def test_exclusive_session_does_not_remove_another_sessions_lock(self):
        self.create()
        with Stack(self.root):
            with self.assertRaisesRegex(StackError,"WORKSPACE_BUSY_OR_STALE"):
                Stack(self.root)
            self.assertTrue((self.root/".writer-lock").is_dir())
        self.assertFalse((self.root/".writer-lock").exists())

    def test_stale_lock_requires_explicit_stopped_assertion(self):
        self.create()
        (self.root/".writer-lock").mkdir()
        with self.assertRaisesRegex(StackError,"WORKSPACE_BUSY_OR_STALE"):
            Stack(self.root)
        with Stack(self.root,confirm_stopped=True) as app:
            with self.assertRaisesRegex(StackError,"STOPPED_ASSERTION_REQUIRED"):
                app.recover()
            self.assertEqual(app.recover(confirm_stopped=True)["review_items"],0)

    def test_recovery_never_deletes_nonempty_lock_content(self):
        self.create()
        lock = self.root/".writer-lock"
        lock.mkdir()
        (lock/"retained.txt").write_text("Fictional retained evidence.",encoding="utf-8")
        with self.assertRaisesRegex(StackError,"LOCK_NOT_EMPTY"):
            Stack(self.root,confirm_stopped=True)
        self.assertTrue((lock/"retained.txt").is_file())

    def test_partial_uncommitted_generation_is_retained_and_ignored(self):
        self.create()
        orphan = self.root/"r000002"
        orphan.mkdir()
        partial = b'{"fictional_partial":'
        (orphan/"state.json").write_bytes(partial)
        with Stack(self.root) as app:
            self.assertEqual(app.status()["orphan_generations"],1)
            app.run("sample","notice",fictional_input())
            self.assertGreater(app.sequence,2)
        self.assertEqual((orphan/"state.json").read_bytes(),partial)

    def test_committed_corruption_is_refused_unchanged(self):
        self.create()
        state = self.root/"r000001"/"state.json"
        state.write_bytes(state.read_bytes()+b" ")
        before = self.hashes()
        with self.assertRaisesRegex(StackError,"JOURNAL_CHAIN_INVALID"):
            Stack(self.root)
        self.assertEqual(self.hashes(),before)

    def test_nonempty_commit_marker_and_unknown_entries_are_refused(self):
        self.create()
        marker = self.root/"r000001"/"COMMITTED"
        marker.write_bytes(b"fictional")
        with self.assertRaises(StackError):
            Stack(self.root)
        marker.write_bytes(b"")
        (self.root/"unrecognized.txt").write_text("fictional",encoding="utf-8")
        with self.assertRaisesRegex(StackError,"WORKSPACE_ENTRY_INVALID"):
            Stack(self.root)

    def test_journal_generation_and_byte_budgets_refuse_before_write(self):
        self.create()
        with Stack(self.root) as app:
            before = self.hashes()
            with mock.patch.object(journal,"MAX_GENERATIONS",app.next_sequence):
                with self.assertRaisesRegex(StackError,"JOURNAL_GENERATION_LIMIT"):
                    app.run("sample","notice",fictional_input())
            with mock.patch.object(journal,"MAX_TOTAL",app.total_bytes):
                with self.assertRaisesRegex(StackError,"JOURNAL_BYTE_LIMIT"):
                    app.run("sample","notice",fictional_input())
            self.assertEqual(self.hashes(),before)

    def test_unconfirmed_state_write_poisons_session_and_preserves_partial_bytes(self):
        self.create()
        original = files.write_new
        def partial(path,raw):
            if Path(path).name=="state.json":
                original(path,raw[:17])
                raise StackError("INJECTED_WRITE_FAILURE")
            return original(path,raw)
        with Stack(self.root) as app:
            with mock.patch.object(files,"write_new",side_effect=partial):
                with self.assertRaisesRegex(StackError,"INJECTED_WRITE_FAILURE"):
                    app.run("sample","notice",fictional_input())
            with self.assertRaisesRegex(StackError,"SESSION_UNAVAILABLE"):
                app.status()
        with Stack(self.root) as app:
            self.assertEqual(app.status()["orphan_generations"],1)
            self.assertEqual(app.status()["runs"],[])

    def test_transport_is_never_called_when_durable_claim_fails(self):
        self.create(run=True)
        fake = FakeTransport()
        with Stack(self.root) as app, mock.patch.object(app,"commit",side_effect=StackError("INJECTED_CLAIM_FAILURE")):
            with self.assertRaisesRegex(StackError,"INJECTED_CLAIM_FAILURE"):
                app.dispatch(fake,now=0)
        self.assertEqual(fake.calls,0)

    def test_accepted_callback_with_failed_result_commit_recovers_without_replay(self):
        self.create(run=True)
        fake = FakeTransport()
        with Stack(self.root) as app:
            original = app.commit
            def commit(value):
                if value["queue"]["notice"]["state"]=="ACCEPTED":
                    raise StackError("INJECTED_ACK_WRITE_FAILURE")
                return original(value)
            with mock.patch.object(app,"commit",side_effect=commit):
                with self.assertRaises(StackError):
                    app.dispatch(fake,now=0)
        self.assertEqual(fake.accepted_keys,("notice",))
        with Stack(self.root) as app:
            self.assertTrue(app.status()["recovery_required"])
            with self.assertRaisesRegex(StackError,"RECOVERY_REQUIRED"):
                app.dispatch(FakeTransport(),now=1)
            app.recover(confirm_stopped=True)
            self.assertEqual(app.queue()[0]["state"],"REVIEW_REQUIRED")
            self.assertEqual(app.dispatch(FakeTransport(),now=1),[])

    def test_committed_marker_after_unconfirmed_ack_is_loaded_on_reopen(self):
        self.create()
        original = files.write_new
        def uncertain(path,raw):
            original(path,raw)
            if Path(path).name=="COMMITTED":
                raise StackError("INJECTED_COMMIT_ACK_FAILURE")
        with Stack(self.root) as app:
            with mock.patch.object(files,"write_new",side_effect=uncertain):
                with self.assertRaises(StackError):
                    app.run("sample","notice",fictional_input())
        with Stack(self.root) as app:
            self.assertEqual(app.result("notice")["state"],"RUNNING")
            self.assertEqual(app.recover(confirm_stopped=True)["review_items"],1)

    def test_output_modes_and_existing_file_refusal(self):
        output = self.parent/"report.json"
        files.write_new(output,b"fictional")
        if os.name!="nt":
            self.assertEqual(stat.S_IMODE(output.stat().st_mode),0o600)
        with self.assertRaises(StackError):
            files.write_new(output,b"changed")
        self.assertEqual(output.read_bytes(),b"fictional")


class FilesystemGuards(Fixture):
    def link_or_skip(self,call):
        try:call()
        except OSError:
            if os.environ.get("STACK_REQUIRE_LINKS")=="1":raise
            self.skipTest("Native link creation unavailable on this test host")

    def test_symlink_input_and_ancestor_are_refused_without_touching_target(self):
        target = self.parent/"target"
        target.mkdir()
        source = target/"input.json"
        source.write_bytes(b"fictional")
        link = self.parent/"linked"
        self.link_or_skip(lambda:os.symlink(target,link,target_is_directory=True))
        with self.assertRaises(StackError):files.read(link/"input.json",64)
        leaf = self.parent/"leaf.json"
        self.link_or_skip(lambda:os.symlink(source,leaf))
        with self.assertRaises(StackError):files.read(leaf,64)
        self.assertEqual(source.read_bytes(),b"fictional")

    def test_hardlinked_input_and_journal_state_are_refused(self):
        self.create()
        state = self.root/"r000001"/"state.json"
        link = self.parent/"linked.json"
        self.link_or_skip(lambda:os.link(state,link))
        with self.assertRaises(StackError):files.read(link,1048576)
        with self.assertRaises(StackError):Stack(self.root)

    def test_symlink_workspace_and_output_parent_are_refused(self):
        target = self.parent/"target"
        target.mkdir()
        link = self.parent/"linked"
        self.link_or_skip(lambda:os.symlink(target,link,target_is_directory=True))
        with self.assertRaises(StackError):Stack(link)
        with self.assertRaises(StackError):files.write_new(link/"new.json",b"fictional")
        self.assertEqual(list(target.iterdir()),[])

    @unittest.skipUnless(os.name=="nt","Windows-only junction and stream checks")
    def test_windows_junction_and_stream_names_are_refused(self):
        target = self.parent/"target"
        target.mkdir()
        link = self.parent/"junction"
        result = subprocess.run(["cmd","/c","mklink","/J",str(link),str(target)],capture_output=True,text=True,timeout=15)
        if result.returncode and os.environ.get("STACK_REQUIRE_LINKS")!="1":
            self.skipTest("Native junction creation unavailable on this test volume")
        self.assertEqual(result.returncode,0)
        try:
            with self.assertRaises(StackError):Stack(link)
            with self.assertRaises(StackError):files.write_new(link/"new.json",b"fictional")
            with self.assertRaises(StackError):files.read(str(target/"input")+":named",64)
        finally:os.rmdir(link)
        self.assertEqual(list(target.iterdir()),[])

    @unittest.skipUnless(os.name!="nt","POSIX-only special-file check")
    def test_posix_fifo_is_refused_without_blocking(self):
        target = self.parent/"fifo"
        os.mkfifo(target)
        with self.assertRaises(StackError):files.read(target,64)


class ProcessRecovery(Fixture):
    def child(self,code):
        return subprocess.run([sys.executable,"-B","-c",code,str(self.root)],
            env={**os.environ,"PYTHONPATH":str(APP),"PYTHONDONTWRITEBYTECODE":"1","PYTHONUTF8":"1"},
            capture_output=True,text=True,timeout=30)

    def test_actual_process_exit_after_run_start_recovers_as_review(self):
        self.create()
        result = self.child("import os,sys;from data_services import service;from data_services.contracts import fictional_input;service._calculate=lambda *a:os._exit(17);app=service.Stack(sys.argv[1]);app.run('sample','crashed',fictional_input())")
        self.assertEqual((result.returncode,result.stderr),(17,""))
        with self.assertRaisesRegex(StackError,"WORKSPACE_BUSY_OR_STALE"):Stack(self.root)
        with Stack(self.root,confirm_stopped=True) as app:
            self.assertEqual(app.recover(confirm_stopped=True)["review_items"],1)
            self.assertEqual(app.result("crashed")["state"],"REVIEW_REQUIRED")
            self.assertEqual(app.queue(),[])

    def test_actual_exit_after_fake_acceptance_never_replays_after_recovery(self):
        self.create(run=True)
        code = """import os,sys
from pathlib import Path
from data_services.service import Stack
class Fake:
 def send(self,message):
  Path(sys.argv[1]).parent.joinpath('fictional-accepted.txt').write_text('one',encoding='utf-8')
  os._exit(19)
app=Stack(sys.argv[1]);app.dispatch(Fake(),now=0)
"""
        result = self.child(code)
        self.assertEqual((result.returncode,result.stderr),(19,""))
        with Stack(self.root,confirm_stopped=True) as app:
            self.assertEqual(app.queue()[0]["state"],"IN_FLIGHT")
            app.recover(confirm_stopped=True)
            fake = FakeTransport()
            self.assertEqual(app.dispatch(fake,now=100),[])
            self.assertEqual(fake.calls,0)
        self.assertEqual((self.parent/"fictional-accepted.txt").read_text(encoding="utf-8"),"one")

    def test_actual_exit_after_claim_before_callback_is_conservatively_held(self):
        self.create(run=True)
        code = "import os,sys;from data_services import service;service.Outbox=lambda **k:os._exit(23);app=service.Stack(sys.argv[1]);app.dispatch(object(),now=0)"
        result = self.child(code)
        self.assertEqual((result.returncode,result.stderr),(23,""))
        with Stack(self.root,confirm_stopped=True) as app:
            app.recover(confirm_stopped=True)
            self.assertEqual(app.queue()[0]["code"],"RESTART_UNCERTAIN")
            self.assertEqual(app.dispatch(FakeTransport(),now=100),[])
