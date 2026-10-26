"""Generated managed workspaces, native primitives and actual process interruption."""
from __future__ import annotations
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import profile_engine as engine
import profile_fs as fs


def tree(path):
    """Byte/tree evidence only; read timestamps and OS permission metadata excluded."""
    path = Path(path)
    if not path.exists(): return None
    result = {}
    for item in sorted(path.rglob('*')):
        name = item.relative_to(path).as_posix()
        result[name] = ('directory', None) if item.is_dir() else ('file', hashlib.sha256(item.read_bytes()).hexdigest())
    return result


class EngineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.workspace = self.base/'workspace'
        self.orchard = self.base/'orchard'
        self.meadow = self.base/'meadow'
        for source, label in [(self.orchard, b'orchard'), (self.meadow, b'meadow')]:
            (source/'settings').mkdir(parents=True)
            (source/'readme.txt').write_bytes(b'Fictional '+label+b' profile\n')
            (source/'settings'/'demo.ini').write_bytes(b'[fictional]\nlabel='+label+b'\n')
        self.originals = (tree(self.orchard), tree(self.meadow))

    def initialize(self):
        value = engine.initialize(self.workspace)
        self.assertEqual(value['status'], 'OK')
        return value

    def imported(self, both=True):
        self.initialize()
        self.assertEqual(engine.import_profile(self.workspace, 'orchard', self.orchard)['status'], 'OK')
        if both: self.assertEqual(engine.import_profile(self.workspace, 'meadow', self.meadow)['status'], 'OK')

    def unchanged_sources(self):
        self.assertEqual((tree(self.orchard), tree(self.meadow)), self.originals)

    def fails(self, function, *arguments):
        with self.assertRaises((engine.ProfileError, OSError)) as raised:
            function(*arguments)
        if isinstance(raised.exception, engine.ProfileError):
            self.assertRegex(str(raised.exception), r'^[A-Z][A-Z0-9_]*$')
        return raised.exception

    def limit(self, name, value):
        stack = ExitStack()
        found = False
        for module in (engine, fs):
            if hasattr(module, name):
                found = True; stack.enter_context(patch.object(module, name, value))
        self.assertTrue(found, 'Documented limit constant is unavailable: '+name)
        return stack

    def state(self):
        return json.loads((self.workspace/'state.json').read_text(encoding='utf-8'))

    def save_state(self, value):
        (self.workspace/'state.json').write_text(json.dumps(value), encoding='utf-8')

    def test_initialization_is_fresh_and_bounded(self):
        self.initialize()
        value = engine.status(self.workspace)
        self.assertEqual(value['status'], 'OK')
        self.assertIsNone(value['active_profile']); self.assertIsNone(value['pending'])
        self.assertEqual(value['profiles'], [])
        self.fails(engine.initialize, self.workspace)
        self.unchanged_sources()

    def test_existing_directory_and_missing_parent_are_refused(self):
        self.workspace.mkdir(); (self.workspace/'untouched.txt').write_bytes(b'keep')
        before = tree(self.workspace)
        self.fails(engine.initialize, self.workspace)
        self.assertEqual(tree(self.workspace), before)
        self.fails(engine.initialize, self.base/'missing'/'store')
        self.assertFalse((self.base/'missing').exists())

    def test_explicit_absolute_paths_required(self):
        self.fails(engine.initialize, Path('relative-store'))
        self.fails(engine.initialize, self.base/'..'/'other')
        self.fails(engine.initialize, '//example.invalid/fictional/store')
        self.assertFalse(self.workspace.exists())

    def test_import_copies_source_and_status_lists_profiles(self):
        self.imported()
        value = engine.status(self.workspace)
        self.assertEqual(value['status'], 'OK')
        self.assertEqual({row['id'] for row in value['profiles']}, {'orchard', 'meadow'})
        self.assertEqual(tree(self.workspace/'profiles/orchard/payload'), tree(self.orchard))
        self.assertEqual(tree(self.workspace/'profiles/meadow/payload'), tree(self.meadow))
        self.unchanged_sources()

    def test_duplicate_profile_refuses_to_replace_imported_bytes(self):
        self.imported(False)
        before = tree(self.workspace/'profiles/orchard')
        self.fails(engine.import_profile, self.workspace, 'orchard', self.meadow)
        self.assertEqual(tree(self.workspace/'profiles/orchard'), before)
        self.unchanged_sources()

    def test_profile_identifiers_are_not_paths(self):
        self.initialize()
        for name in ('../escape', 'UPPER', 'two words', '-dash', '', 'x'*41, 'a/b', 'a\\b'):
            with self.subTest(name=name): self.fails(engine.import_profile, self.workspace, name, self.orchard)
        self.assertEqual(engine.status(self.workspace)['profiles'], [])

    def test_import_overlap_and_non_directory_are_refused(self):
        self.initialize()
        self.fails(engine.import_profile, self.workspace, 'bad', self.workspace)
        self.fails(engine.import_profile, self.workspace, 'bad', self.base)
        self.fails(engine.import_profile, self.workspace, 'bad', self.orchard/'readme.txt')
        self.assertEqual(engine.status(self.workspace)['profiles'], [])
        self.unchanged_sources()

    def test_plan_reads_without_creating_operation_or_changing_state(self):
        self.imported()
        before = tree(self.workspace)
        value = engine.plan(self.workspace, 'activate', 'orchard')
        self.assertEqual(value['status'], 'OK'); self.assertTrue(value['allowed'])
        self.assertEqual(value['action'], 'activate'); self.assertEqual(value['profile'], 'orchard')
        self.assertEqual(tree(self.workspace), before)
        self.unchanged_sources()

    def test_activation_switch_and_deactivation_retain_prior_trees(self):
        self.imported()
        self.assertEqual(engine.activate(self.workspace, 'orchard')['status'], 'OK')
        self.assertEqual(tree(self.workspace/'active'), tree(self.orchard))
        self.assertEqual(engine.status(self.workspace)['active_profile'], 'orchard')
        self.assertEqual(engine.activate(self.workspace, 'meadow')['status'], 'OK')
        self.assertEqual(tree(self.workspace/'active'), tree(self.meadow))
        self.assertEqual(engine.status(self.workspace)['active_profile'], 'meadow')
        retained = list((self.workspace/'operations').glob('*/previous'))
        self.assertTrue(any(tree(path)==tree(self.orchard) for path in retained))
        self.assertEqual(engine.deactivate(self.workspace)['status'], 'OK')
        self.assertFalse((self.workspace/'active').exists())
        final = engine.status(self.workspace)
        self.assertEqual(final['status'], 'OK'); self.assertIsNone(final['active_profile'])
        retained = list((self.workspace/'operations').glob('*/previous'))
        self.assertTrue(any(tree(path)==tree(self.meadow) for path in retained))
        self.assertGreaterEqual(len(final['history']), 3)
        self.unchanged_sources()

    def test_reactivation_uses_verified_private_profile_copy(self):
        self.imported(False); engine.activate(self.workspace, 'orchard'); engine.deactivate(self.workspace)
        (self.orchard/'readme.txt').write_bytes(b'local source changed after import')
        engine.activate(self.workspace, 'orchard')
        self.assertEqual(tree(self.workspace/'active'), self.originals[0])

    def test_plan_is_revalidated_at_activation(self):
        self.imported(); engine.activate(self.workspace, 'orchard')
        engine.plan(self.workspace, 'activate', 'meadow')
        (self.workspace/'active/readme.txt').write_bytes(b'drift after preview')
        before = tree(self.workspace/'active')
        self.fails(engine.activate, self.workspace, 'meadow')
        self.assertEqual(tree(self.workspace/'active'), before)
        self.unchanged_sources()

    def test_changed_active_file_is_visible_and_held(self):
        self.imported(); engine.activate(self.workspace, 'orchard')
        (self.workspace/'active/readme.txt').write_bytes(b'changed')
        self.assertEqual(engine.status(self.workspace)['status'], 'REVIEW_REQUIRED')
        before = tree(self.workspace)
        self.fails(engine.deactivate, self.workspace)
        self.assertEqual(tree(self.workspace), before)

    def test_unexpected_active_file_is_never_moved_or_deleted(self):
        self.imported(); engine.activate(self.workspace, 'orchard')
        marker = self.workspace/'active/unexpected.txt'; marker.write_bytes(b'leave this alone')
        self.assertEqual(engine.status(self.workspace)['status'], 'REVIEW_REQUIRED')
        self.fails(engine.activate, self.workspace, 'meadow')
        self.assertEqual(marker.read_bytes(), b'leave this alone')
        self.assertEqual(engine.status(self.workspace)['active_profile'], 'orchard')

    def test_unexpected_empty_active_directory_is_drift(self):
        self.imported(); engine.activate(self.workspace, 'orchard')
        directory = self.workspace/'active/unexpected-empty'; directory.mkdir()
        self.assertEqual(engine.status(self.workspace)['status'], 'REVIEW_REQUIRED')
        self.fails(engine.deactivate, self.workspace)
        self.assertTrue(directory.is_dir())

    def test_missing_active_payload_is_drift(self):
        self.imported(); engine.activate(self.workspace, 'orchard')
        (self.workspace/'active/readme.txt').unlink()
        self.assertEqual(engine.status(self.workspace)['status'], 'REVIEW_REQUIRED')
        self.fails(engine.activate, self.workspace, 'meadow')

    def test_tampered_imported_payload_prevents_activation(self):
        self.imported(False)
        target = self.workspace/'profiles/orchard/payload/readme.txt'; target.write_bytes(b'drift')
        self.fails(engine.activate, self.workspace, 'orchard')
        self.assertFalse((self.workspace/'active').exists())
        self.unchanged_sources()

    def test_unmanaged_active_directory_is_not_adopted_or_overwritten(self):
        self.imported(False)
        (self.workspace/'active').mkdir(); marker=self.workspace/'active/foreign.txt'; marker.write_bytes(b'keep')
        self.fails(engine.activate, self.workspace, 'orchard')
        self.assertEqual(marker.read_bytes(), b'keep')
        self.assertIsNone(engine.status(self.workspace)['active_profile'])

    def test_json_duplicate_keys_and_unknown_fields_are_refused(self):
        self.initialize()
        state = self.workspace/'state.json'; original=state.read_bytes()
        state.write_bytes(b'{"schema_version":1,"schema_version":1,"active_profile":null,"pending":null}')
        self.fails(engine.status, self.workspace)
        state.write_bytes(original)
        value = self.state(); value['unexpected'] = 'fictional'; self.save_state(value)
        self.fails(engine.status, self.workspace)

    def test_invalid_state_types_and_traversal_pending_are_refused(self):
        self.initialize(); original=self.state()
        for changed in ({'schema_version':True}, {'active_profile':True}, {'pending':'../escape'}):
            with self.subTest(fields=tuple(changed)):
                value=dict(original,**changed);self.save_state(value)
                self.fails(engine.recover, self.workspace)
        self.assertFalse((self.base/'escape').exists())

    def test_owner_metadata_cannot_gain_unexpected_fields(self):
        self.initialize(); owner=self.workspace/'owner.json'
        value=json.loads(owner.read_text());value['extra']='fictional';owner.write_text(json.dumps(value))
        self.fails(engine.status,self.workspace)

    def test_profile_manifest_unknown_field_is_refused(self):
        self.imported(False); manifest=self.workspace/'profiles/orchard/manifest.json'
        value=json.loads(manifest.read_text());value['extra']='fictional';manifest.write_text(json.dumps(value))
        self.fails(engine.activate,self.workspace,'orchard')
        self.assertFalse((self.workspace/'active').exists())

    def test_profile_count_limit_refuses_before_creating_operation(self):
        self.imported(False);before=tree(self.workspace)
        with self.limit('MAX_PROFILES',1):self.fails(engine.import_profile,self.workspace,'meadow',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.unchanged_sources()

    def test_actual_file_byte_limit_refuses_before_creating_operation(self):
        self.initialize();(self.meadow/'oversized.bin').write_bytes(b'x'*(fs.MAX_FILE_BYTES+1))
        before=tree(self.workspace);source_before=tree(self.meadow)
        self.fails(engine.import_profile,self.workspace,'large',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.assertEqual(tree(self.meadow),source_before)

    def test_lowered_file_byte_limit_refuses_before_creating_operation(self):
        self.initialize();before=tree(self.workspace)
        with self.limit('MAX_FILE_BYTES',16):self.fails(engine.import_profile,self.workspace,'bounded',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.unchanged_sources()

    def test_total_byte_limit_refuses_before_creating_operation(self):
        self.initialize();before=tree(self.workspace)
        with self.limit('MAX_TOTAL_BYTES',32):self.fails(engine.import_profile,self.workspace,'bounded',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.unchanged_sources()

    def test_file_count_limit_refuses_before_creating_operation(self):
        self.initialize();before=tree(self.workspace)
        with self.limit('MAX_FILES',1):self.fails(engine.import_profile,self.workspace,'bounded',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.unchanged_sources()

    def test_directory_count_limit_refuses_before_creating_operation(self):
        self.initialize();(self.meadow/'another-empty').mkdir();before=tree(self.workspace)
        with self.limit('MAX_DIRECTORIES',1):self.fails(engine.import_profile,self.workspace,'bounded',self.meadow)
        self.assertEqual(tree(self.workspace),before)

    def test_relative_path_limit_refuses_before_creating_operation(self):
        self.initialize();before=tree(self.workspace)
        with self.limit('MAX_PATH',10):self.fails(engine.import_profile,self.workspace,'bounded',self.meadow)
        self.assertEqual(tree(self.workspace),before);self.unchanged_sources()

    def test_metadata_byte_limit_refuses_without_rewriting_state(self):
        self.initialize();state=self.workspace/'state.json'
        state.write_bytes(b' '*(fs.MAX_JSON+1));before=tree(self.workspace)
        self.fails(engine.recover,self.workspace)
        self.assertEqual(tree(self.workspace),before)

    def test_malformed_manifest_fields_are_fixed_failures(self):
        self.imported(False);manifest=self.workspace/'profiles/orchard/manifest.json'
        original=json.loads(manifest.read_text())
        mutations=[
            lambda value:value.update(schema_version=True),
            lambda value:value.update(directories=['settings',4]),
            lambda value:value.update(files=[None]),
            lambda value:value['files'][0].update(bytes=True),
            lambda value:value['files'][0].update(path='../escape'),
            lambda value:value['files'][0].update(sha256='not-a-hash'),
            lambda value:value.update(total_bytes=True),
            lambda value:value.update(digest='0'*64),
            lambda value:value.update(directories=[]),
        ]
        for number,change in enumerate(mutations):
            with self.subTest(mutation=number):
                value=copy.deepcopy(original);change(value);manifest.write_text(json.dumps(value))
                before=tree(self.workspace);self.fails(engine.activate,self.workspace,'orchard')
                self.assertEqual(tree(self.workspace),before)
        self.assertFalse((self.base/'escape').exists());self.unchanged_sources()

    def test_operation_limit_refuses_mutation(self):
        self.imported(False)
        count=len(list((self.workspace/'operations').iterdir()))
        with self.limit('MAX_OPERATIONS',count):self.fails(engine.activate,self.workspace,'orchard')
        self.assertFalse((self.workspace/'active').exists())

    def test_empty_pre_intent_orphan_is_retained_and_does_not_brick_activation(self):
        self.imported(False);orphan=self.workspace/'operations'/('1'*32);orphan.mkdir()
        value=engine.status(self.workspace)
        self.assertEqual(value['status'],'REVIEW_REQUIRED')
        self.assertIn('RETAINED_PREPARATION',{row['code'] for row in value['issues']})
        self.assertTrue(any(row['id']==orphan.name and row['outcome']=='retained_preparation' for row in value['history']))
        self.assertIsNone(value['pending']);self.assertTrue(engine.plan(self.workspace,'activate','orchard')['allowed'])
        self.assertEqual(engine.activate(self.workspace,'orchard')['status'],'OK')
        self.assertEqual(tree(self.workspace/'active'),tree(self.orchard))
        self.assertTrue(orphan.is_dir());self.assertEqual(list(orphan.iterdir()),[])
        self.unchanged_sources()

    def test_pre_intent_temporary_metadata_is_retained_without_rewriting(self):
        self.imported(False);orphan=self.workspace/'operations'/('2'*32);orphan.mkdir()
        temporary=orphan/('.tmp-'+'3'*32);temporary.write_bytes(b'{"fictional":"incomplete')
        before=tree(self.workspace)
        self.assertEqual(engine.status(self.workspace)['status'],'REVIEW_REQUIRED')
        self.assertEqual(engine.recover(self.workspace)['outcome'],'no_pending_operation')
        self.assertEqual(tree(self.workspace),before)

    def test_unknown_pre_intent_entries_are_held(self):
        self.initialize();orphan=self.workspace/'operations'/('4'*32);orphan.mkdir()
        (orphan/'stage').mkdir();(orphan/'stage/unknown.txt').write_bytes(b'retain unknown payload')
        before=tree(self.workspace);self.fails(engine.recover,self.workspace)
        self.assertEqual(tree(self.workspace),before)

    def test_pending_token_cannot_reference_pre_intent_orphan(self):
        self.initialize();token='5'*32;(self.workspace/'operations'/token).mkdir()
        state=self.state();state['pending']=token;self.save_state(state)
        before=tree(self.workspace);self.fails(engine.recover,self.workspace)
        self.assertEqual(tree(self.workspace),before)

    def test_interrupted_operation_preparation_remains_recoverable(self):
        self.imported(False)
        code='''from pathlib import Path
import os,sys
sys.path.insert(0,sys.argv[1])
import profile_engine as engine
import profile_fs as fs
original=fs.save_json
def interrupt_before_intent(path,value):
    if Path(path).name=='intent.json':os._exit(67)
    return original(path,value)
fs.save_json=interrupt_before_intent
engine.activate(Path(sys.argv[2]),'orchard')
raise SystemExit(68)
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT),str(self.workspace)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,67,result.stderr)
        self.assertIsNone(engine.status(self.workspace)['pending'])
        self.assertEqual(engine.status(self.workspace)['status'],'REVIEW_REQUIRED')
        self.assertEqual(engine.activate(self.workspace,'orchard')['status'],'OK')
        self.assertEqual(tree(self.workspace/'active'),tree(self.orchard));self.unchanged_sources()

    def test_case_colliding_files_are_refused_where_representable(self):
        self.initialize(); first=self.orchard/'Case.cfg';other=self.orchard/'case.cfg'
        first.write_bytes(b'first');other.write_bytes(b'second')
        if os.path.samefile(first,other):self.skipTest('Filesystem cannot represent distinct case-colliding names')
        self.fails(engine.import_profile,self.workspace,'collision',self.orchard)

    def test_hardlinked_source_is_refused(self):
        self.initialize(); linked=self.orchard/'alias.txt'
        try:os.link(self.orchard/'readme.txt',linked)
        except OSError:self.skipTest('Hardlink creation unavailable')
        self.fails(engine.import_profile,self.workspace,'linked',self.orchard)

    def test_symlink_source_and_linked_parent_are_refused(self):
        self.initialize(); linked=self.base/'source-link'
        try:linked.symlink_to(self.orchard,target_is_directory=True)
        except OSError:self.skipTest('Symlink creation unavailable')
        self.fails(engine.import_profile,self.workspace,'linked',linked)
        route=self.base/'parent-link';route.symlink_to(self.base,target_is_directory=True)
        self.fails(engine.status,route/'workspace')

    def test_symlink_payload_entry_is_refused(self):
        self.initialize(); linked=self.orchard/'linked.txt'
        try:linked.symlink_to(self.orchard/'readme.txt')
        except OSError:self.skipTest('Symlink creation unavailable')
        self.fails(engine.import_profile,self.workspace,'linked',self.orchard)

    @unittest.skipUnless(hasattr(os,'mkfifo'),'POSIX FIFO fixture only')
    def test_special_fifo_source_is_refused_without_opening(self):
        self.initialize(); os.mkfifo(self.orchard/'pipe')
        self.fails(engine.import_profile,self.workspace,'special',self.orchard)

    @unittest.skipUnless(os.name=='nt','Windows alternate-stream path syntax only')
    def test_windows_stream_and_reserved_workspace_paths_are_refused(self):
        self.fails(engine.initialize,str(self.workspace)+':stream')
        for name in ('CON','NUL','CONIN$','CONOUT$','name.','name '):
            with self.subTest(name=name):self.fails(engine.initialize,self.base/name)

    @unittest.skipUnless(os.name=='nt','Windows named data streams only')
    def test_windows_named_source_stream_is_refused(self):
        self.initialize();stream=Path(str(self.meadow/'readme.txt')+':private-stream')
        try:stream.write_bytes(b'fictional stream payload')
        except OSError as error:self.skipTest('Named stream creation unavailable (error '+str(error.errno)+')')
        before=tree(self.workspace)
        self.fails(engine.import_profile,self.workspace,'streamed',self.meadow)
        self.assertEqual(tree(self.workspace),before)

    def test_native_directory_rename_refuses_existing_empty_destination(self):
        source=self.base/'rename-source';destination=self.base/'rename-destination'
        source.mkdir();destination.mkdir();(source/'kept.txt').write_bytes(b'kept')
        self.fails(fs.rename_no_replace,source,destination)
        self.assertEqual((source/'kept.txt').read_bytes(),b'kept')
        self.assertEqual(list(destination.iterdir()),[])

    def test_native_directory_rename_commits_only_to_new_destination(self):
        source=self.base/'rename-source';destination=self.base/'rename-destination'
        source.mkdir();(source/'kept.txt').write_bytes(b'kept')
        fs.rename_no_replace(source,destination)
        self.assertFalse(source.exists());self.assertEqual((destination/'kept.txt').read_bytes(),b'kept')

    def test_native_rename_race_does_not_replace_new_empty_directory(self):
        source=self.base/'race-source';destination=self.base/'race-destination'
        source.mkdir();(source/'kept.txt').write_bytes(b'kept')
        if os.name=='nt':
            original=fs.os.rename
            def race(left,right):
                destination.mkdir()
                return original(left,right)
            with patch.object(fs.os,'rename',side_effect=race):
                self.fails(fs.rename_no_replace,source,destination)
        elif sys.platform.startswith('linux'):
            library=fs.ctypes.CDLL(None,use_errno=True);native=getattr(library,'renameat2',None)
            if native is None:self.skipTest('libc renameat2 unavailable')
            native.argtypes=[fs.ctypes.c_int,fs.ctypes.c_char_p,fs.ctypes.c_int,fs.ctypes.c_char_p,fs.ctypes.c_uint]
            native.restype=fs.ctypes.c_int
            def race(*arguments):
                destination.mkdir()
                return native(*arguments)
            with patch.object(fs.ctypes,'CDLL',return_value=SimpleNamespace(renameat2=race)):
                self.fails(fs.rename_no_replace,source,destination)
        else:self.skipTest('Only the documented Windows/Linux primitives are tested')
        self.assertEqual((source/'kept.txt').read_bytes(),b'kept')
        self.assertTrue(destination.is_dir());self.assertEqual(list(destination.iterdir()),[])

    def test_nonblocking_lock_contention_uses_another_process(self):
        self.initialize()
        code='''from pathlib import Path
import sys
sys.path.insert(0,sys.argv[1])
import profile_fs as fs
with fs.lock_workspace(Path(sys.argv[2])):
    print('LOCKED',flush=True)
    sys.stdin.readline()
'''
        child=subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT),str(self.workspace)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def cleanup():
            if child.poll() is None:child.communicate('\n',timeout=10)
            else:child.communicate(timeout=10)
        self.addCleanup(cleanup)
        messages=queue.Queue();threading.Thread(target=lambda:messages.put(child.stdout.readline()),daemon=True).start()
        self.assertEqual(messages.get(timeout=10).strip(),'LOCKED')
        started=time.monotonic();self.fails(engine.status,self.workspace)
        self.assertLess(time.monotonic()-started,2,'Workspace lock acquisition must be nonblocking')
        child.communicate('\n',timeout=10)
        self.assertEqual(engine.status(self.workspace)['status'],'OK')

    def interrupt(self,phase,action='activate'):
        code='''from pathlib import Path
import os,sys
sys.path.insert(0,sys.argv[1])
import profile_engine as engine
def stop(stage):
    if stage==sys.argv[3]:os._exit(67)
workspace=Path(sys.argv[2])
if sys.argv[4]=='activate':engine.activate(workspace,'meadow',fault_hook=stop)
else:engine.deactivate(workspace,fault_hook=stop)
raise SystemExit(68)
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT),str(self.workspace),phase,action],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,67,(phase,result.stdout,result.stderr))

    def recover_child(self):
        code='''from pathlib import Path
import json,sys
sys.path.insert(0,sys.argv[1])
import profile_engine as engine
print(json.dumps(engine.recover(Path(sys.argv[2]))))
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT),str(self.workspace)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def check_recovery(self,phase):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt(phase)
        result=self.recover_child();self.assertEqual(result['status'],'OK')
        value=engine.status(self.workspace);self.assertEqual(value['status'],'OK');self.assertIsNone(value['pending'])
        expected=self.orchard if phase=='after_intent_written' else self.meadow
        self.assertEqual(tree(self.workspace/'active'),tree(expected))
        self.assertEqual(value['active_profile'],'orchard' if phase=='after_intent_written' else 'meadow')
        self.assertEqual(result['outcome'],'aborted_incomplete_stage' if phase=='after_intent_written' else 'complete')
        before=tree(self.workspace);self.assertEqual(self.recover_child()['status'],'OK')
        self.assertEqual(tree(self.workspace),before,'Recovery must be repeatable without content changes')
        self.unchanged_sources()

    def test_process_recovery_after_intent(self):self.check_recovery('after_intent_written')
    def test_process_recovery_after_stage_verification(self):self.check_recovery('after_stage_verified')
    def test_process_recovery_after_previous_rename(self):self.check_recovery('after_previous_retained')
    def test_process_recovery_after_active_rename(self):self.check_recovery('after_active_committed')
    def test_process_recovery_after_state_write(self):self.check_recovery('after_state_saved')

    def test_pending_operation_blocks_other_mutations(self):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt('after_stage_verified')
        before=tree(self.workspace)
        self.fails(engine.activate,self.workspace,'orchard');self.fails(engine.deactivate,self.workspace)
        self.fails(engine.import_profile,self.workspace,'third',self.orchard)
        self.assertEqual(tree(self.workspace),before)

    def test_pending_operation_cannot_claim_unrelated_active_profile(self):
        self.imported();engine.import_profile(self.workspace,'third',self.orchard)
        engine.activate(self.workspace,'orchard');self.interrupt('after_stage_verified')
        state=self.state();state['active_profile']='third';self.save_state(state)
        before=tree(self.workspace)
        error=self.fails(engine.recover,self.workspace)
        self.assertEqual(str(error),'PENDING_STATE_INCONSISTENT');self.assertEqual(tree(self.workspace),before)

    def test_partial_stage_is_retained_during_safe_abort(self):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt('after_intent_written')
        pending=self.state()['pending'];stage=self.workspace/'operations'/pending/'stage';stage.mkdir(exist_ok=True)
        partial=stage/'readme.txt';partial.write_bytes(b'partial')
        result=self.recover_child();self.assertEqual(result['status'],'OK')
        self.assertEqual(result['outcome'],'aborted_incomplete_stage')
        self.assertEqual(tree(self.workspace/'active'),tree(self.orchard))
        self.assertTrue(partial.exists());self.assertEqual(partial.read_bytes(),b'partial')
        self.assertIsNone(engine.status(self.workspace)['pending'])

    def test_interrupted_import_copy_is_aborted_and_partial_bytes_retained(self):
        self.imported(False);engine.import_profile(self.workspace,'unrelated',self.orchard)
        engine.activate(self.workspace,'orchard')
        code='''from pathlib import Path
import os,sys
sys.path.insert(0,sys.argv[1])
import profile_engine as engine
import profile_fs as fs
original=fs.write_new
def stop_during_payload(path,data,*arguments,**keywords):
    path=Path(path)
    if path.name=='readme.txt' and path.parent.name=='payload' and 'operations' in path.parts:
        original(path,data[:max(1,len(data)//2)],*arguments,**keywords)
        os._exit(67)
    return original(path,data,*arguments,**keywords)
fs.write_new=stop_during_payload
engine.import_profile(Path(sys.argv[2]),'extra',Path(sys.argv[3]))
raise SystemExit(68)
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT),str(self.workspace),str(self.meadow)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,67,result.stderr)
        pending=self.state()['pending'];partial=self.workspace/'operations'/pending/'stage/payload/readme.txt'
        saved=partial.read_bytes();self.assertGreater(len(saved),0)
        self.assertLess(len(saved),len((self.meadow/'readme.txt').read_bytes()))
        original=self.state();self.save_state(dict(original,active_profile='unrelated'));before=tree(self.workspace)
        error=self.fails(engine.recover,self.workspace)
        self.assertEqual(str(error),'PENDING_STATE_INCONSISTENT');self.assertEqual(tree(self.workspace),before)
        self.save_state(original)
        recovered=self.recover_child();self.assertEqual(recovered['outcome'],'aborted_incomplete_stage')
        self.assertEqual(partial.read_bytes(),saved)
        self.assertEqual(tree(self.workspace/'active'),tree(self.orchard))
        value=engine.status(self.workspace);self.assertEqual(value['status'],'OK')
        self.assertEqual({row['id'] for row in value['profiles']},{'orchard','unrelated'})
        self.unchanged_sources()

    def test_unexpected_incomplete_stage_entry_is_held(self):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt('after_intent_written')
        stage=self.workspace/'operations'/self.state()['pending']/'stage';stage.mkdir()
        marker=stage/'unrelated.txt';marker.write_bytes(b'unknown data must remain')
        before=tree(self.workspace);self.fails(engine.recover,self.workspace)
        self.assertEqual(tree(self.workspace),before);self.assertEqual(marker.read_bytes(),b'unknown data must remain')

    def test_recovery_refuses_unexpected_destination_after_old_rename(self):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt('after_previous_retained')
        active=self.workspace/'active';active.mkdir();marker=active/'unrelated.txt';marker.write_bytes(b'never replace')
        self.fails(engine.recover,self.workspace)
        self.assertEqual(marker.read_bytes(),b'never replace')
        self.assertTrue(any(tree(path)==tree(self.orchard) for path in (self.workspace/'operations').glob('*/previous')))

    def test_recovery_refuses_changed_candidate_after_commit(self):
        self.imported();engine.activate(self.workspace,'orchard');self.interrupt('after_active_committed')
        marker=self.workspace/'active/readme.txt';marker.write_bytes(b'changed candidate')
        self.fails(engine.recover,self.workspace)
        self.assertEqual(marker.read_bytes(),b'changed candidate')

    def test_process_recovery_finishes_deactivation_after_previous_rename(self):
        self.imported(False);engine.activate(self.workspace,'orchard');self.interrupt('after_previous_retained','deactivate')
        self.assertEqual(self.recover_child()['status'],'OK')
        value=engine.status(self.workspace);self.assertEqual(value['status'],'OK');self.assertIsNone(value['active_profile'])
        self.assertFalse((self.workspace/'active').exists());self.unchanged_sources()

    def test_pending_deactivation_rejects_unrelated_state_without_moving_data(self):
        self.imported();engine.activate(self.workspace,'orchard')
        self.interrupt('after_previous_retained','deactivate')
        original=self.state();self.save_state(dict(original,active_profile='meadow'));before=tree(self.workspace)
        error=self.fails(engine.recover,self.workspace)
        self.assertEqual(str(error),'PENDING_STATE_INCONSISTENT');self.assertEqual(tree(self.workspace),before)
        self.save_state(original);self.assertEqual(self.recover_child()['status'],'OK');self.unchanged_sources()

    def test_recover_without_pending_operation_has_no_content_side_effect(self):
        self.imported(False);before=tree(self.workspace)
        self.assertEqual(engine.recover(self.workspace)['status'],'OK')
        self.assertEqual(tree(self.workspace),before)

    def terminal_pending_case(self, action, invalid):
        self.imported();engine.activate(self.workspace,'orchard')
        if action=='abort':self.interrupt('after_intent_written')
        original_save=fs.save_json
        def stop_before_pending_clear(path,value):
            if Path(path)==self.workspace/'state.json' and value.get('pending') is None:
                raise RuntimeError('fictional interruption before final pending clear')
            return original_save(path,value)
        with patch.object(fs,'save_json',stop_before_pending_clear):
            with self.assertRaises(RuntimeError):
                if action=='activate':engine.activate(self.workspace,'meadow')
                elif action=='deactivate':engine.deactivate(self.workspace)
                else:engine.recover(self.workspace)
        valid=self.state();intent=json.loads((self.workspace/'operations'/valid['pending']/'intent.json').read_text())
        self.assertEqual(intent['phase'],'aborted' if action=='abort' else 'complete')
        self.save_state(dict(valid,active_profile=invalid));before=tree(self.workspace)
        error=self.fails(engine.recover,self.workspace)
        self.assertEqual(str(error),'PENDING_STATE_INCONSISTENT')
        self.assertEqual(tree(self.workspace),before)
        self.save_state(valid);self.assertEqual(self.recover_child()['status'],'OK')
        self.assertIsNone(self.state()['pending']);self.unchanged_sources()

    def test_terminal_activation_requires_committed_active_state(self):
        self.terminal_pending_case('activate','orchard')

    def test_terminal_deactivation_requires_disabled_state(self):
        self.terminal_pending_case('deactivate','orchard')

    def test_terminal_abort_requires_previous_active_state(self):
        self.terminal_pending_case('abort','meadow')


if __name__=='__main__':unittest.main()
