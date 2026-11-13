"""Copied CLI consumers of authored disposable Git repositories only."""
import ctypes
from ctypes import wintypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("git_worktree_report.py", "examples/make_demo.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_stream_and_alias_containment"
PROCESS_WINDOWS_REASON = "Native Windows junction and alias fixture"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_metadata_refused"
PROCESS_POSIX_REASON = "Native POSIX FIFO and socket fixture"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_repository_metadata_git_and_output_refused"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
PROBE = r'''
import importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import git_worktree_report as m
assert Path(m.__file__).resolve()==base/'git_worktree_report.py'
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'))
 import make_demo
 assert Path(make_demo.__file__).resolve()==base/'examples/make_demo.py'
 assert make_demo.r is m
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)))
 raise SystemExit(0)
elif kind=='manifest_failure':
 original=os.open
 def opening(path,flags,*extra,**options):
  if Path(path).name=='MANIFEST.json' and flags&os.O_WRONLY:
   raise OSError('FICTIONAL_PRIVATE_OUTPUT_DETAIL')
  return original(path,flags,*extra,**options)
 os.open=opening
elif kind in ('version_bound','status_bound'):
 original=m.run_bounded
 def bounded(arguments,**options):
  if (kind=='version_bound' and '--version' in arguments) or (kind=='status_bound' and 'status' in arguments):
   options['maximum']=1 if kind=='version_bound' else 32
  return original(arguments,**options)
 m.run_bounded=bounded
elif kind=='metadata_mutation':
 original=m.metadata_receipt;events=[]
 def receipt(gitdir,common):
  value=original(gitdir,common)
  if not events:
   path=common/'config'
   with path.open('ab') as handle:handle.write(b'\n# Controlled fictional concurrent change\n')
   events.append(True)
  return value
 m.metadata_receipt=receipt
elif kind=='nul':
 raise SystemExit(m.main(['--repo',str(Path(args[1]).parent/'FICTIONAL\x00PRIVATE'),'--git-executable',args[0],'--output',args[1]]))
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(m.main(args))
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def entry(path, index=".", worktree=".", kind="tracked", **extra):
    return dict(kind=kind, path=path, index_status=index, worktree_status=worktree,
                submodule=None, **extra)


class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get("OUTLANDS_TEST_GIT")
        expected = os.environ.get("OUTLANDS_TEST_GIT_SHA256")
        version = os.environ.get("OUTLANDS_TEST_GIT_VERSION")
        if not value or not expected or not version:
            raise AssertionError("EXPLICIT_PINNED_GIT_REQUIRED")
        cls.git_executable = Path(value)
        if not cls.git_executable.is_absolute() or not cls.git_executable.is_file():
            raise AssertionError("ABSOLUTE_REAL_GIT_REQUIRED")
        cls.git_pin = sha(cls.git_executable.read_bytes())
        if cls.git_pin != expected or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise AssertionError("PINNED_GIT_BYTES_DIFFER")
        cls.git_bytes = cls.git_executable.stat().st_size
        wanted = "git version 2.56.1.windows.1" if os.name == "nt" else "git version 2.56.1"
        if version != wanted:
            raise AssertionError("PINNED_GIT_VERSION_DIFFERS")
        cls.git_version_line = wanted
        result = subprocess.run([str(cls.git_executable), "--version"], stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=30, env=cls.environment())
        if result.returncode != 0 or result.stderr or result.stdout.rstrip(b"\r\n").decode() != wanted:
            raise AssertionError("ACTUAL_PINNED_GIT_VERSION_DIFFERS")

    @classmethod
    def tearDownClass(cls):
        if sha(cls.git_executable.read_bytes()) != cls.git_pin or cls.git_executable.stat().st_size != cls.git_bytes:
            raise AssertionError("TRUSTED_GIT_BYTES_CHANGED")

    @staticmethod
    def environment():
        env = {k: v for k, v in os.environ.items()
               if not k.upper().startswith(("PYTHON", "PIP_", "GIT_", "GCM_", "SSH_"))
               and k.upper() not in {"PAGER", "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"}}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1",
                   GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1",
                   GIT_NO_REPLACE_OBJECTS="1", GIT_ALLOW_PROTOCOL="", LC_ALL="C", LANG="C")
        return env

    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="gwr-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.copy = self.work / "copied runtime"
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT / name).read_bytes()
            target = self.copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            self.pins[name] = sha(raw)
        self.home = self.work / "isolated home"
        self.home.mkdir()
        self.env = self.environment()
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), XDG_CONFIG_HOME=str(self.home),
                        GIT_AUTHOR_DATE="@1000000000 +0000", GIT_COMMITTER_DATE="@1000000000 +0000")
        self.repo = self.work / "fictional repository"
        self.repo.mkdir()
        self.git("init", "--initial-branch=main", "--object-format=sha1")
        self.git("config", "core.autocrlf", "false")
        for name, data in {"alpha.txt": b"Fictional base line\n", "rename source.txt": b"Fictional rename baseline\n",
                           "overlap.txt": b"Fictional overlap baseline\n"}.items():
            (self.repo / name).write_bytes(data)
        self.git("add", ".")
        self.git("commit", "-m", "Authored fictional baseline")
        self.output = self.work / "new report"
        self.addCleanup(self.runtime_preserved)

    def git(self, *args, repo=None, check=True):
        repo = self.repo if repo is None else repo
        command = [str(self.git_executable), "--no-optional-locks", "-c", "core.hooksPath=" + os.devnull,
                   "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "diff.external=",
                   "-c", "user.name=Fictional Example", "-c", "user.email=example@example.invalid",
                   "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-C", str(repo), *args]
        result = subprocess.run(command, env=self.env, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace")[:1000])
        return result

    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({n: sha((self.copy / n).read_bytes()) for n in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])

    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix()
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    rows[key] = ("LINK", os.readlink(path))
                elif path.is_dir():
                    rows[key] = ("DIRECTORY",)
                    visit(path)
                else:
                    info = path.lstat()
                    if stat.S_ISREG(info.st_mode):
                        rows[key] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns,
                                     info.st_ctime_ns, info.st_ino, info.st_nlink)
                    else:
                        rows[key] = ("SPECIAL", info.st_mode)
        visit(self.work)
        return rows

    def expected(self, rows=(), *, repo=None, branch="main", state="branch", upstream=None):
        repo = self.repo if repo is None else repo
        head = None if state == "unborn" else self.git("rev-parse", "HEAD", repo=repo).stdout.decode().strip()
        status = self.git("status", "--porcelain=v2", "-z", "--branch", "--ahead-behind",
                          "--untracked-files=all", "--ignored=no", "--ignore-submodules=all", "--renames", repo=repo).stdout
        rows = sorted(rows, key=lambda row: row["path"])
        counts = dict(untracked=sum(r["kind"] == "untracked" for r in rows),
                      unmerged=sum(r["kind"] == "unmerged" for r in rows),
                      staged=sum(r["kind"] not in {"untracked", "unmerged"} and r["index_status"] != "." for r in rows),
                      unstaged=sum(r["kind"] not in {"untracked", "unmerged"} and r["worktree_status"] != "." for r in rows))
        return dict(schema_version=1, tool="git-worktree-reporter", head_oid=head,
                    branch=None if state == "detached" else branch, head_state=state,
                    upstream=upstream or dict(name=None, ahead=None, behind=None,
                       basis="stored_local_refs_only_no_network_refresh", comparison="unavailable"),
                    entry_count=len(rows), entries=rows, counts=counts, ignored_header_count=0,
                    status_sha256=sha(status),
                    coverage="selected_worktree_status_excluding_ignored_and_submodule_contents",
                    interpretation="Git status observations under isolated configuration, not a backup, content inventory, secret scan, ownership or publication clearance.",
                    git_version="2.56.1", observed_control_files_unchanged=True,
                    configuration="global_system_disabled_local_includes_filters_partial_clones_refused",
                    subprocess_limits=dict(seconds_each=15, stdout_bytes=8 * 1024 * 1024, stderr_bytes=65536, max_entries=10000))

    def call(self, *, repo=None, output=None, git=None, args=None, expected=None, error=None,
             probe=None, allow=(), ignore=(), env_extra=None, demo=False, help_output=False):
        repo = self.repo if repo is None else repo
        output = self.output if output is None else output
        git = self.git_executable if git is None else git
        if args is None:
            args = (["--destination", output, "--git-executable", git] if demo else
                    ["--repo", repo, "--git-executable", git, "--output", output])
        before = self.snapshot()
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        command = ([sys.executable, "-I", "-B", "-W", "error", "-c", PROBE, str(self.copy), probe]
                   if probe else [sys.executable, "-I", "-B", "-W", "error",
                                  str(self.copy / ("examples/make_demo.py" if demo else "git_worktree_report.py"))])
        done = subprocess.run([*command, *map(str, args)], cwd=self.work, env=env,
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
        self.assertEqual(done.returncode, 2 if error else 0, (done.stdout + done.stderr).decode(errors="replace")[:2000])
        self.assertEqual(done.stderr, b"")
        for private in (str(self.work).encode(), b"FICTIONAL_PRIVATE", b"Traceback", b"example.invalid/private"):
            self.assertNotIn(private, done.stdout)
        after = self.snapshot()
        ignored = {Path(path).relative_to(self.work).as_posix() for path in ignore}
        self.assertEqual({k: v for k, v in before.items() if k not in ignored},
                         {k: after.get(k) for k in before if k not in ignored})
        for key in after.keys() - before.keys():
            path = self.work / key
            self.assertTrue(any(path == Path(root) or path.is_relative_to(root) for root in allow),
                            "Unexpected application write: " + key)
        self.runtime_preserved()
        if help_output:
            self.assertIn(b"--git-executable", done.stdout)
            return None
        if probe == "affinity":
            wanted = dict(status="COPIED_RUNTIME_AFFINITY", dependencies=0)
        elif demo:
            wanted = dict(status="INCOMPLETE", error="DEMO_CREATION_FAILED") if error else dict(status="FICTIONAL_REPOSITORY_CREATED", expected_entries=3)
        elif error:
            wanted = dict(status="INCOMPLETE", error=error)
        else:
            self.assertIsNotNone(expected)
            wanted = dict(status="LOCAL_STATUS_RECORDED", head_state=expected["head_state"],
                          entry_count=expected["entry_count"], counts=expected["counts"])
        self.assertEqual(len(done.stdout.splitlines()), 1)
        self.assertEqual(json.loads(done.stdout), wanted)
        self.assertEqual(done.stdout, json.dumps(wanted, sort_keys=not demo and probe != "affinity").encode() + NEWLINE)
        if not error and expected is not None:
            self.check_report(output, expected)
        return wanted

    def check_report(self, output, expected):
        self.assertEqual({p.name for p in output.iterdir()}, {"report.json", "MANIFEST.json"})
        raw = (output / "report.json").read_bytes()
        self.assertEqual(json.loads(raw), expected)
        self.assertEqual(raw, (json.dumps(expected, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode())
        manifest = dict(schema_version=1, files=[dict(path="report.json", bytes=len(raw), sha256=sha(raw))])
        self.assertEqual((output / "MANIFEST.json").read_bytes(), (json.dumps(manifest, indent=2) + "\n").encode())
        self.assertNotIn(str(self.work).encode(), raw)
        self.assertNotIn(b"Fictional base line", raw)
        self.assertNotIn(b"example.invalid/private", raw)

    def report(self, rows=(), **options):
        repo = options.get("repo", self.repo)
        expected = self.expected(rows, repo=repo, **options.pop("expect_options", {}))
        return self.call(expected=expected, allow=[options.get("output", self.output)], **options)

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314 and os.environ.get("OUTLANDS_GIT_REPORTER_REQUIRE_LINKS") != "1":
                self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_and_demo_import_affinity(self):
        self.call(args=[], probe="affinity")

    def test_demo_cli_reports_complete_authored_status(self):
        demo = self.work / "new authored demo"
        self.call(output=demo, demo=True, allow=[demo])
        self.report([entry("README.md", worktree="M"), entry("staged.txt", index="M"),
                     entry("new item.txt", index="?", worktree="?", kind="untracked")], repo=demo)
        self.call(output=demo, demo=True, error="DEMO_CREATION_FAILED")

    def test_clean_branch_full_report_and_manifest(self):
        self.report()
        self.assertEqual((self.repo / ".git/HEAD").read_bytes(), b"ref: refs/heads/main\n")

    def test_unborn_staged_and_untracked_state(self):
        unborn = self.work / "unborn"
        unborn.mkdir()
        self.git("init", "--initial-branch=main", "--object-format=sha1", repo=unborn)
        (unborn / "staged.txt").write_bytes(b"Fictional unborn staged\n")
        (unborn / "untracked.txt").write_bytes(b"Fictional unborn untracked\n")
        self.git("add", "staged.txt", repo=unborn)
        self.report([entry("staged.txt", index="A"), entry("untracked.txt", index="?", worktree="?", kind="untracked")],
                    repo=unborn, expect_options=dict(state="unborn"))

    def test_staged_and_unstaged_counts_overlap_for_one_file(self):
        path = self.repo / "overlap.txt"
        path.write_bytes(b"Fictional staged update\n")
        self.git("add", "overlap.txt")
        path.write_bytes(b"Fictional later unstaged update\n")
        self.report([entry("overlap.txt", index="M", worktree="M")])

    def test_detached_head_keeps_object_id_without_branch(self):
        self.git("checkout", "--detach", "HEAD")
        self.report(expect_options=dict(state="detached"))

    def test_conflicted_merge_has_separate_unmerged_count(self):
        self.git("checkout", "-b", "fictional-side")
        (self.repo / "alpha.txt").write_bytes(b"Fictional side\n")
        self.git("commit", "-am", "Fictional side change")
        self.git("checkout", "main")
        (self.repo / "alpha.txt").write_bytes(b"Fictional main\n")
        self.git("commit", "-am", "Fictional main change")
        conflict = self.git("merge", "fictional-side", check=False)
        self.assertEqual(conflict.returncode, 1)
        self.report([entry("alpha.txt", index="U", worktree="U", kind="unmerged")])

    def test_staged_rename_preserves_original_and_spaced_paths(self):
        self.git("mv", "rename source.txt", "renamed item.txt")
        self.report([entry("renamed item.txt", index="R", kind="renamed_or_copied",
                           original_path="rename source.txt", similarity="R100")])

    def test_linked_worktree_preserves_common_and_pointer_metadata(self):
        linked = self.work / "linked worktree"
        self.git("worktree", "add", "-b", "fictional-linked", str(linked))
        self.report(repo=linked, expect_options=dict(branch="fictional-linked"))
        for output in (self.repo / ".git/forbidden", self.repo / ".git/worktrees/forbidden", linked / "forbidden"):
            self.call(repo=linked, output=output,
                      error="OUTPUT_INSIDE_WORKTREE" if output.is_relative_to(linked) else "OUTPUT_INSIDE_GIT_METADATA")

    def test_diverged_upstream_counts_use_stored_local_refs_only(self):
        self.git("branch", "fictional-base")
        self.git("checkout", "fictional-base")
        (self.repo / "side.txt").write_bytes(b"Fictional upstream only\n")
        self.git("add", "side.txt")
        self.git("commit", "-m", "Fictional upstream change")
        self.git("checkout", "main")
        (self.repo / "local.txt").write_bytes(b"Fictional local only\n")
        self.git("add", "local.txt")
        self.git("commit", "-m", "Fictional local change")
        self.git("branch", "--set-upstream-to=fictional-base")
        self.git("config", "remote.origin.url", "https://example.invalid/private")
        self.git("config", "credential.helper", "!echo FICTIONAL_PRIVATE_MUST_NOT_RUN")
        self.report(expect_options=dict(upstream=dict(name="fictional-base", ahead=1, behind=1,
                    basis="stored_local_refs_only_no_network_refresh", comparison="available")))

    def test_missing_upstream_comparison_is_null_not_zero(self):
        self.git("config", "branch.main.remote", ".")
        self.git("config", "branch.main.merge", "refs/heads/fictional-missing")
        self.report(expect_options=dict(upstream=dict(name="fictional-missing", ahead=None, behind=None,
                    basis="stored_local_refs_only_no_network_refresh", comparison="unavailable")))

    def test_ignored_paths_excluded_and_nested_repository_refused(self):
        (self.repo / ".gitignore").write_bytes(b"ignored-*\n")
        self.git("add", ".gitignore")
        self.git("commit", "-m", "Fictional ignore rule")
        (self.repo / "ignored-private.txt").write_bytes(b"FICTIONAL_PRIVATE_IGNORED")
        self.report()
        nested = self.repo / "nested"
        nested.mkdir()
        self.git("init", "--initial-branch=main", "--object-format=sha1", repo=nested)
        (nested / "fictional.txt").write_bytes(b"Fictional nested content\n")
        # Git emits an untracked directory record; the existing portable parser
        # deliberately remains unchanged and refuses its trailing slash.
        target = self.work / "nested unsupported report"
        self.call(output=target, error="STATUS_PATH_UNSUPPORTED")
        self.assertFalse(target.exists())

    def test_utf8_spaced_names_are_json_data_without_payload_bodies(self):
        name = "fictional \u03bb spaced.txt"
        (self.repo / name).write_bytes(b"FICTIONAL_PRIVATE_BODY")
        self.report([entry(name, index="?", worktree="?", kind="untracked")])
        raw = (self.output / "report.json").read_bytes()
        self.assertIn(b"\\u03bb", raw)
        self.assertNotIn(b"FICTIONAL_PRIVATE_BODY", raw)

    def test_argument_errors_and_help_have_fixed_redacted_output(self):
        for args in ([], ["--repo", self.repo], ["--unknown", "FICTIONAL_PRIVATE"], ["--repo", self.repo, "--git-executable", self.git_executable]):
            self.call(args=args, error="ARGUMENTS_INVALID")
        self.call(args=["--help"], help_output=True)
        self.call(args=[self.git_executable, self.output], probe="nul", error="INVALID_LOCAL_PATH")

    def test_git_selection_requires_explicit_absolute_regular_executable(self):
        self.call(git="git", error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        self.call(git=self.copy, error="TRUSTED_GIT_EXECUTABLE_REQUIRED")
        self.call(git=self.work / "missing git.exe", error="IO_OR_GIT_INPUT_ERROR")
        if os.name == "nt":
            batch = self.work / "not git.cmd"
            batch.write_bytes(b"@echo FICTIONAL_PRIVATE\n")
            self.call(git=batch, error="TRUSTED_GIT_EXECUTABLE_REQUIRED")

    def test_nonroot_or_missing_worktree_inputs_are_incomplete(self):
        subdir = self.repo / "subdirectory"
        subdir.mkdir()
        self.call(repo=subdir, error="IO_OR_GIT_INPUT_ERROR")
        self.call(repo=self.work / "missing", error="IO_OR_GIT_INPUT_ERROR")
        self.call(repo="relative", error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        self.call(repo=self.repo / "alpha.txt", error="WORKTREE_DIRECTORY_REQUIRED")

    def test_outputs_are_new_external_and_require_existing_parent(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_bytes(b"Fictional keep\n")
        self.call(error="FRESH_OUTPUT_REQUIRED")
        for path, error in ((self.repo / "forbidden", "OUTPUT_INSIDE_WORKTREE"),
                            (self.repo / ".git/forbidden", "OUTPUT_INSIDE_WORKTREE"),
                            (self.work / "absent/new", "IO_OR_GIT_INPUT_ERROR")):
            self.call(output=path, error=error)
        self.assertFalse((self.work / "absent").exists())

    def test_local_filter_configuration_is_refused_before_execution(self):
        marker = self.work / "helper executed.txt"
        self.git("config", "filter.fictional.clean", "echo FICTIONAL_PRIVATE > " + marker.as_posix())
        (self.repo / ".gitattributes").write_bytes(b"*.txt filter=fictional\n")
        self.call(error="CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED")
        self.assertFalse(marker.exists())

    def test_local_config_includes_are_refused_without_expansion(self):
        included = self.work / "untrusted include"
        included.write_bytes(b"FICTIONAL_PRIVATE_INVALID_CONFIG")
        self.git("config", "include.path", str(included))
        self.call(error="CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED")
        self.assertEqual(included.read_bytes(), b"FICTIONAL_PRIVATE_INVALID_CONFIG")

    def test_worktree_filter_configuration_is_also_refused(self):
        self.git("config", "extensions.worktreeConfig", "true")
        self.git("config", "--worktree", "filter.fictional.clean", "FICTIONAL_PRIVATE_INVALID_HELPER")
        self.call(error="CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED")

    def test_configured_helpers_and_unsupported_layout_keys_are_refused(self):
        keys = ("diff.fictional.textconv", "diff.fictional.command", "core.sparseCheckout",
                "core.worktree", "core.alternateRefsCommand", "remote.origin.promisor")
        for key in keys:
            with self.subTest(key=key):
                value = ("true" if key in {"core.sparseCheckout", "remote.origin.promisor"}
                         else str(self.repo) if key == "core.worktree" else "FICTIONAL_PRIVATE_HELPER")
                self.git("config", key, value)
                self.call(error="CONFIGURED_HELPER_OR_LAYOUT_UNSUPPORTED")
                self.git("config", "--unset", key)

    def test_hooks_fsmonitor_external_diff_and_pagers_are_inert(self):
        trap = self.work / "helper executed.txt"
        command = 'echo FICTIONAL_PRIVATE > "' + trap.as_posix() + '"'
        self.git("config", "core.fsmonitor", command)
        self.git("config", "diff.external", command)
        self.git("config", "core.pager", command)
        hooks = self.repo / ".git/hooks"
        hook = hooks / "post-index-change"
        hook.write_bytes(("#!/bin/sh\n" + command + "\n").encode())
        hook.chmod(0o700)
        (self.repo / "alpha.txt").write_bytes(b"Fictional unstaged edit\n")
        self.report([entry("alpha.txt", worktree="M")], env_extra={"PAGER": command, "GIT_PAGER": command})
        self.assertFalse(trap.exists())

    def test_inherited_git_routing_and_global_filters_are_isolated(self):
        poison = self.work / "poison global"
        poison.write_bytes(b"[filter \"fictional\"]\n clean = FICTIONAL_PRIVATE_INVALID_HELPER\n[include]\n path = missing-fictional\n")
        self.report(env_extra={"GIT_DIR": str(self.work / "missing"), "GIT_WORK_TREE": str(self.work / "missing"),
                    "GIT_INDEX_FILE": str(self.work / "invented-index"), "GIT_CONFIG_GLOBAL": str(poison),
                    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "filter.injected.clean",
                    "GIT_CONFIG_VALUE_0": "FICTIONAL_PRIVATE_INVALID_HELPER", "GIT_SSH_COMMAND": "FICTIONAL_PRIVATE_SSH",
                    "GCM_INTERACTIVE": "always"})

    def test_shallow_grafts_and_alternate_stores_are_refused(self):
        for name in ("shallow", "info/grafts", "objects/info/alternates", "objects/info/http-alternates"):
            path = self.repo / ".git" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"Fictional unsupported metadata\n")
            self.call(error="SHALLOW_GRAFT_OR_ALTERNATE_UNSUPPORTED")
            path.unlink()

    def test_native_symlink_repository_metadata_git_and_output_refused(self):
        link = self.work / "linked repository"
        self.symlink(link, self.repo, directory=True)
        self.call(repo=link, error="LINKED_PATH_REJECTED")
        git_link = self.work / ("linked git.exe" if os.name == "nt" else "linked-git")
        self.symlink(git_link, self.git_executable)
        self.call(git=git_link, error="LINKED_PATH_REJECTED")
        parent = self.work / "linked output parent"
        self.symlink(parent, self.home, directory=True)
        self.call(output=parent / "new report", error="LINKED_PATH_REJECTED")
        head = self.repo / ".git/HEAD"
        saved = self.repo / ".git/HEAD.saved"
        head.rename(saved)
        self.symlink(head, saved)
        self.call(error="LINKED_PATH_REJECTED")

    @unittest.skipUnless(os.name == "nt", PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_stream_and_alias_containment(self):
        junction = self.work / "junction"
        done = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.repo)],
                              capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.assertTrue(junction.is_junction())
        self.addCleanup(lambda: os.rmdir(junction) if junction.is_junction() else None)
        self.call(repo=junction, error="LINKED_PATH_REJECTED")
        self.call(output=junction / "forbidden", error="LINKED_PATH_REJECTED")
        self.call(repo=str(self.repo) + ":fictional", error="DEVICE_OR_STREAM_PATH_REJECTED")
        self.call(repo="\\\\?\\" + str(self.repo), error="LOCAL_ABSOLUTE_PATH_REQUIRED")
        native = ctypes.WinDLL("kernel32", use_last_error=True)
        getshort = native.GetShortPathNameW
        getshort.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        getshort.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        count = getshort(str(self.repo), buffer, len(buffer))
        self.assertTrue(0 < count < len(buffer))
        # The API may return the same path on volumes without short aliases.
        self.call(output=Path(buffer.value) / "forbidden", error="OUTPUT_INSIDE_WORKTREE")

    @unittest.skipUnless(os.name != "nt", PROCESS_POSIX_REASON)
    def test_native_posix_special_metadata_refused(self):
        head = self.repo / ".git/HEAD"
        original = head.read_bytes()
        head.unlink()
        os.mkfifo(head)
        self.call(error="METADATA_FILE_UNSUPPORTED")
        head.unlink()
        head.write_bytes(original)
        config = self.repo / ".git/config"
        config.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(config))
            self.call(error="METADATA_FILE_UNSUPPORTED")

    def test_bounded_actual_git_output_refuses_incomplete_reports(self):
        for kind in ("version_bound", "status_bound"):
            with self.subTest(bound=kind):
                self.call(probe=kind, error="GIT_OUTPUT_LIMIT")
                self.assertFalse(self.output.exists())

    def test_manifest_write_failure_retains_new_report_without_overwrite(self):
        expected = self.expected()
        self.call(probe="manifest_failure", error="IO_OR_GIT_INPUT_ERROR", allow=[self.output])
        self.assertEqual({p.name for p in self.output.iterdir()}, {"report.json"})
        raw = (json.dumps(expected, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()
        self.assertEqual((self.output / "report.json").read_bytes(), raw)
        self.call(error="FRESH_OUTPUT_REQUIRED")

    def test_observed_config_mutation_refuses_report_creation(self):
        path = self.repo / ".git/config"
        before = path.read_bytes()
        self.call(probe="metadata_mutation", error="REPOSITORY_METADATA_CHANGED", ignore=[path])
        self.assertEqual(path.read_bytes(), before + b"\n# Controlled fictional concurrent change\n")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
