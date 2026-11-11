"""Actual copied-runtime CLI checks using only authored private fixtures."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("release_audit.py", "audit_windows.py")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="audit-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied runtime"
        self.runtime.mkdir()
        self.runtime_hashes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.runtime / name).write_bytes(data)
            self.runtime_hashes[name] = hashlib.sha256(data).hexdigest()
        self.root = self.work / "FICTIONAL_PRIVATE_EXPORT"
        self.root.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, name, body=b"Fictional documentation.\n", *, exported=True):
        path = (self.root if exported else self.work) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path

    def control(self, name, value):
        return self.fixture(name, json.dumps(value).encode("utf-8"), exported=False)

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import release_audit as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, script=None, json_output=True):
        retained = {path: digest(path) for path in self.work.rglob("*")
                    if not path.is_symlink() and not path.is_junction() and stat.S_ISREG(path.lstat().st_mode)}
        result = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8",
                                 str(script or self.runtime / "release_audit.py"), *map(str, arguments)],
                                cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=40)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        for path, checksum in retained.items():
            self.assertEqual(digest(path), checksum)
        self.assertEqual({p.name for p in self.runtime.iterdir()}, set(RUNTIME))
        self.assertEqual({name: digest(self.runtime / name) for name in RUNTIME}, self.runtime_hashes)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), result.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", result.stdout)
        if not json_output:
            return result.stdout
        self.assertEqual(len(result.stdout.splitlines()), 1)
        summary = json.loads(result.stdout)
        if expected in (2, 130):
            self.assertEqual(summary, dict(status="ERROR", code="AUDIT_INTERRUPTED" if expected == 130
                                           else "AUDIT_INPUT_OR_OUTPUT_ERROR"))
        else:
            self.assertEqual(set(summary), {"status", "files", "findings", "errors"})
            self.assertEqual(summary["status"], "NO_PATTERN_FINDINGS" if expected == 0 else "REVIEW_REQUIRED")
        return summary

    def run_cli(self, *arguments, root=None, **options):
        return self.process("--root", self.root if root is None else root, *arguments, **options)

    def report(self, *arguments, expected=0, script=None, root=None):
        self.serial += 1
        path = self.work / ("report-" + str(self.serial) + ".json")
        summary = self.run_cli(*arguments, "--report", path, expected=expected, script=script, root=root)
        raw = path.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"\r\n", raw)
        result = json.loads(raw)
        self.assertEqual(result["status"], summary["status"])
        return result, summary

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_AUDIT_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_clean_summary_report_schema_and_no_implicit_output(self):
        self.fixture("README.md", b"Fictional example: writer@example.invalid 192.0.2.7 2001:db8::1\n")
        self.assertEqual(self.run_cli(), dict(status="NO_PATTERN_FINDINGS", files=1, findings={}, errors=[]))
        self.assertEqual({p.name for p in self.work.iterdir()}, {self.root.name, self.runtime.name})
        result, _ = self.report()
        self.assertEqual(set(result), {"schema_version", "status", "inventory", "findings", "errors", "excluded", "scope"})
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["scope"], dict(max_entries=20000, max_file_bytes=2*1024*1024,
                                             max_total_bytes=64*1024*1024,
                                             bytes_read=(self.root / "README.md").stat().st_size,
                                             git_history_scanned=False, semantic_ip_review=False))

    def test_known_findings_have_rule_and_line_without_matched_snippets(self):
        body = (b"-----BEGIN PRIVATE KEY-----\npassword='fictional-credential'\n"
                b"writer@fictional.local\n10.44.55.66\nhttps://fictional-user:fictional-pass@intranet/\n")
        self.fixture("sample.txt", body)
        result, summary = self.report(expected=1)
        self.assertTrue({"PRIVATE_KEY", "CREDENTIAL_ASSIGNMENT", "EMAIL", "INTERNAL_HOSTNAME",
                         "NETWORK_ADDRESS", "URL_CREDENTIALS", "SINGLE_LABEL_HOST"}.issubset(summary["findings"]))
        for row in result["findings"]:
            self.assertEqual(set(row), {"path", "rule", "line"})
            self.assertEqual(row["path"], "sample.txt")
            self.assertIsInstance(row["line"], int)
        encoded = json.dumps(result)
        for literal in ("fictional-credential", "fictional-user", "10.44.55.66", "BEGIN PRIVATE KEY"):
            self.assertNotIn(literal, encoded)

    def test_private_literals_are_casefolded_and_relative_names_remain_in_private_report(self):
        marker = "FICTIONAL_PRIVATE_MARKER"
        name = marker.lower() + ".txt"
        self.fixture(name, ("prefix " + marker.swapcase() + " suffix\n").encode())
        deny = self.control("deny.json", [marker])
        result, summary = self.report("--deny-file", deny, expected=1)
        self.assertEqual(summary["findings"], {"PATH_PRIVATE_LITERAL": 1, "PRIVATE_LITERAL": 1})
        self.assertEqual({row["path"] for row in result["findings"]}, {name})
        self.assertNotIn("prefix", json.dumps(result))
        self.assertNotIn(str(deny), json.dumps(result))

    def test_exact_manifest_create_compare_and_output_readback(self):
        bodies = {"z.txt": b"Fictional z\r\n", "nested/a.md": b"\xef\xbb\xbfFictional a\n", "LICENSE": b"Fictional license\n"}
        for name, body in bodies.items():
            self.fixture(name, body)
        expected = [dict(path=name, size=len(bodies[name]), sha256=hashlib.sha256(bodies[name]).hexdigest())
                    for name in sorted(bodies)]
        manifest = self.work / "inventory.json"
        self.run_cli("--write-manifest", manifest)
        self.assertEqual(json.loads(manifest.read_bytes()), dict(schema_version=1, inventory=expected))
        result, summary = self.report("--manifest", manifest)
        self.assertEqual(result["inventory"], expected)
        self.assertEqual(summary["files"], 3)
        self.assertTrue(manifest.read_bytes().endswith(b"\n"))

    def test_manifest_detects_changed_added_and_removed_selected_files(self):
        path = self.fixture("a.txt", b"original fictional body\n")
        manifest = self.work / "inventory.json"
        self.run_cli("--write-manifest", manifest)
        for action in ("changed", "added", "removed"):
            with self.subTest(action=action):
                path.write_bytes(b"changed fictional body\n" if action == "changed" else b"original fictional body\n")
                added = self.root / "b.txt"
                if added.exists():
                    added.unlink()
                if action == "added":
                    added.write_bytes(b"fictional addition\n")
                if action == "removed":
                    path.unlink()
                result, summary = self.report("--manifest", manifest, expected=1)
                self.assertEqual(summary["errors"], ["MANIFEST_MISMATCH"])
                self.assertEqual(result["errors"], ["MANIFEST_MISMATCH"])

    def test_invalid_manifest_schema_rows_paths_and_casefold_duplicates_are_errors(self):
        valid = dict(path="a.txt", size=0, sha256=hashlib.sha256(b"").hexdigest())
        cases = [[], {}, dict(schema_version=2, inventory=[]), dict(schema_version=1, inventory=[None])]
        for field, value in (("path", "../a.txt"), ("path", "/a.txt"), ("path", "a\\b.txt"),
                             ("path", "a:stream"), ("path", "a//b.txt"), ("size", True),
                             ("size", -1), ("sha256", "A"*64)):
            cases.append(dict(schema_version=1, inventory=[dict(valid, **{field: value})]))
        cases.append(dict(schema_version=1, inventory=[valid, dict(valid, path="A.TXT")]))
        for index, data in enumerate(cases):
            with self.subTest(index=index):
                self.run_cli("--manifest", self.control("invalid-manifest.json", data), expected=2)

    def test_outputs_are_new_only_outside_export_and_preserve_existing_files(self):
        self.fixture("a.txt")
        existing = self.fixture("FICTIONAL_PRIVATE_existing.json", b"Retain owned output", exported=False)
        directory = self.work / "existing-directory"
        directory.mkdir()
        for option in ("--report", "--write-manifest"):
            for output in (existing, directory, self.root / "inside.json", self.work / "missing-parent" / "out.json"):
                with self.subTest(option=option, kind=output.name):
                    self.run_cli(option, output, expected=2)
        self.assertEqual(existing.read_bytes(), b"Retain owned output")
        self.assertFalse((self.root / "inside.json").exists())

    def test_deny_controls_reject_invalid_values_and_enforce_sixteen_mib(self):
        for index, data in enumerate(({}, ["xy"], [3], ["x"*1025], ["abc"]*1001)):
            self.run_cli("--deny-file", self.control("bad-deny-" + str(index) + ".json", data), expected=2)
        for index, data in enumerate((b"[", b"\xff", b"\xef\xbb\xbf[]")):
            path = self.fixture("malformed-deny-" + str(index) + ".json", data, exported=False)
            self.run_cli("--deny-file", path, expected=2)
        exact = self.fixture("exact-control.json", b"[]" + b" "*(16*1024*1024-2), exported=False)
        self.run_cli("--deny-file", exact)
        over = self.fixture("over-control.json", exact.read_bytes() + b" ", exported=False)
        self.run_cli("--deny-file", over, expected=2)

    def test_text_two_mib_limit_counts_raw_bom_bytes_and_keeps_unknown_scope(self):
        limit = 2*1024*1024
        self.fixture("exact.txt", b"\xef\xbb\xbf" + b" "*(limit-3))
        self.fixture("over.txt", b" "*(limit+1))
        self.fixture("unknown.blob", b" "*(limit+1))
        result, summary = self.report(expected=1)
        self.assertEqual(summary["findings"], {"BINARY_OR_UNKNOWN_FORMAT_REVIEW": 1, "SIZE_LIMIT": 1})
        self.assertEqual([row["path"] for row in result["inventory"]], ["exact.txt"])
        self.assertEqual(result["scope"]["bytes_read"], limit)
        self.assertEqual(result["inventory"][0]["size"], limit)

    def test_non_utf8_binary_sensitive_names_and_private_directories_need_review(self):
        self.fixture("bad.txt", b"\xff")
        self.fixture("embedded-zero.txt", b"a\x00b")
        self.fixture("data.bin", b"\x00\xff")
        self.fixture(".env", b"Fictional blocked content")
        self.fixture("private/hidden.txt", b"Fictional blocked content")
        self.fixture(".git/config", b"Fictional excluded content")
        result, summary = self.report(expected=1)
        self.assertEqual(summary["findings"], dict(NON_UTF8_REVIEW=1, BINARY_CONTENT_REVIEW=1,
                                                  BINARY_OR_UNKNOWN_FORMAT_REVIEW=1, SENSITIVE_FILENAME=1,
                                                  PRIVATE_OR_RUNTIME_DIRECTORY=1))
        self.assertEqual(result["excluded"], [".git"])
        self.assertEqual(result["inventory"], [])
        self.assertEqual(result["scope"]["bytes_read"], 4)

    def test_inventory_and_findings_have_deterministic_exact_path_order(self):
        bodies = {"z.txt": b"10.11.12.13\n", "A.txt": b"a@fictional.local\n", "nested/b.txt": b"-----BEGIN PRIVATE KEY-----\n"}
        for name in reversed(list(bodies)):
            self.fixture(name, bodies[name])
        first, _ = self.report(expected=1)
        second, _ = self.report(expected=1)
        self.assertEqual(first, second)
        self.assertEqual([row["path"] for row in first["inventory"]], sorted(bodies))
        self.assertEqual(first["findings"], sorted(first["findings"], key=lambda row: (row["path"], row["line"] or 0, row["rule"])))
        for row in first["inventory"]:
            self.assertEqual(row["sha256"], hashlib.sha256(bodies[row["path"]]).hexdigest())

    def test_help_explicit_root_and_fixed_argument_or_io_errors(self):
        help_text = self.process("--help", json_output=False)
        self.assertIn("--write-manifest", help_text)
        self.assertIn("--deny-file", help_text)
        for arguments in ((), ("--root",), ("--unknown", "FICTIONAL_PRIVATE_ARGUMENT"),
                          ("--root", self.work / "FICTIONAL_PRIVATE_MISSING")):
            self.process(*arguments, expected=2)
        file = self.fixture("not-a-root.txt", exported=False)
        self.run_cli(root=file, expected=2)
        self.fixture("a.md")
        self.run_cli(root=self.root.name)

    def test_copied_runtime_does_not_execute_inputs_or_use_network(self):
        self.fixture("fictional.py", b"raise RuntimeError('FICTIONAL_PRIVATE_NEVER_EXECUTE')\n")
        self.fixture("links.md", b"https://example.invalid/fictional\n")
        script = self.wrapper("", prelude="""
            import socket, urllib.request, subprocess, runpy
            def forbidden(*args, **kwargs):
                raise AssertionError('Input execution or network attempted')
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            """)
        result, summary = self.report(script=script)
        self.assertEqual(summary["files"], 2)
        self.assertEqual({row["path"] for row in result["inventory"]}, {"fictional.py", "links.md"})

    def test_native_hardlink_sources_are_preserved_and_existing_outputs_refused(self):
        source = self.fixture("a.txt", b"Fictional shared unnamed bytes\n")
        sibling = self.work / "hardlink-source.txt"
        os.link(source, sibling)
        self.assertGreaterEqual(source.stat().st_nlink, 2)
        result, _ = self.report()
        self.assertEqual(result["inventory"][0]["sha256"], digest(sibling))
        output = self.work / "hardlinked-output.json"
        os.link(source, output)
        for option in ("--report", "--write-manifest"):
            self.run_cli(option, output, expected=2)
        control = self.control("deny-hardlink.json", [])
        alias = self.work / "deny-hardlink-alias.json"
        os.link(control, alias)
        self.run_cli("--deny-file", alias, expected=2 if os.name == "nt" else 0)
        self.assertEqual(source.read_bytes(), sibling.read_bytes())

    def test_complete_looking_report_is_retained_after_controlled_late_readback_failure(self):
        self.fixture("a.txt")
        output = self.work / "complete-looking.json"
        script = self.wrapper("""
            original = tool.write_new
            def write(path, data, root):
                original(path, data, root)
                # A failed consumer readback after creation cannot certify success.
                events.append(True)
                raise OSError('FICTIONAL_PRIVATE_READBACK_FAILURE')
            tool.write_new = write
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli("--report", output, script=script, expected=2)
        retained = json.loads(output.read_bytes())
        self.assertEqual(retained["status"], "NO_PATTERN_FINDINGS")
        self.assertEqual(len(retained["inventory"]), 1)

    @unittest.skipUnless(os.name == "nt", "Native Windows output fixture")
    def test_native_windows_short_zero_and_flush_outputs_are_handled(self):
        self.fixture("a.txt")
        for mode in ("short", "zero", "flush"):
            output = self.work / (mode + ".json")
            script = self.wrapper("""
                backend = tool._windows()
                original_write, original_sync = backend.os.write, backend.os.fsync
                def write(fd, block):
                    events.append('write')
                    if MODE == 'zero':
                        return 0
                    return original_write(fd, block[:7] if MODE == 'short' else block)
                def sync(fd):
                    events.append('flush')
                    if MODE == 'flush':
                        raise OSError('FICTIONAL_PRIVATE_FLUSH_FAILURE')
                    return original_sync(fd)
                backend.os.write, backend.os.fsync = write, sync
                """.replace("MODE", repr(mode)), postlude="assert events and status == " + ("0" if mode == "short" else "2") + "\n")
            self.run_cli("--report", output, script=script, expected=0 if mode == "short" else 2)
            self.assertTrue(output.is_file())
            if mode == "zero":
                self.assertEqual(output.read_bytes(), b"")
            else:
                self.assertEqual(json.loads(output.read_bytes())["status"], "NO_PATTERN_FINDINGS")

    @unittest.skipUnless(os.name == "nt", "Native Windows interruption fixture")
    def test_native_windows_interrupt_retains_partial_report(self):
        self.fixture("a.txt")
        output = self.work / "interrupted.json"
        script = self.wrapper("""
            backend = tool._windows()
            original = backend.os.write
            def interrupted(fd, block):
                original(fd, block[:5])
                events.append(True)
                raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT_DETAIL')
            backend.os.write = interrupted
            """, postlude="assert events == [True] and status == 130\n")
        self.run_cli("--report", output, script=script, expected=130)
        self.assertEqual(output.stat().st_size, 5)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(output.read_bytes())

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_alternate_stream_scope_and_refusals(self):
        source = self.fixture("a.txt")
        stream = str(source) + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"Fictional stream omitted from unnamed inventory")
        result, summary = self.report()
        self.assertEqual(summary["files"], 1)
        self.assertEqual(result["inventory"][0]["sha256"], digest(source))
        for option in ("--deny-file", "--manifest", "--report", "--write-manifest"):
            self.run_cli(option, stream, expected=2)
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"Fictional stream omitted from unnamed inventory")

    def test_native_symlink_root_is_refused(self):
        self.fixture("a.txt")
        alias = self.work / "linked-root"
        self.symlink(alias, self.root, directory=True)
        self.run_cli(root=alias, expected=2)

    def test_native_linked_controls_and_export_entries_are_refused(self):
        deny = self.control("deny.json", [])
        manifest = self.control("manifest.json", dict(schema_version=1, inventory=[]))
        for option, target in (("--deny-file", deny), ("--manifest", manifest)):
            alias = self.work / (target.stem + "-link.json")
            self.symlink(alias, target)
            self.run_cli(option, alias, expected=2)
        binary = self.fixture("owned-large-target.bin", b"\xff"*(2*1024*1024+1), exported=False)
        directory = self.work / "owned-directory"
        directory.mkdir()
        (directory / "never-read.txt").write_bytes(b"10.11.12.13\n")
        self.symlink(self.root / "linked.txt", binary)
        self.symlink(self.root / "linked-folder", directory, directory=True)
        result, summary = self.report(expected=1)
        self.assertEqual(summary["findings"], {"LINK_OR_REPARSE": 2})
        self.assertEqual(result["scope"]["bytes_read"], 0)
        self.assertEqual(result["inventory"], [])

    def test_native_symlink_output_parent_and_existing_leaf_preserve_targets(self):
        self.fixture("a.txt")
        target = self.fixture("retained-target.json", b"Retain fictional target", exported=False)
        alias = self.work / "existing-leaf.json"
        self.symlink(alias, target)
        folder = self.work / "owned-output-directory"
        folder.mkdir()
        linked = self.work / "linked-output-parent"
        self.symlink(linked, folder, directory=True)
        for option in ("--report", "--write-manifest"):
            self.run_cli(option, alias, expected=2)
            self.run_cli(option, linked / "out.json", expected=2)
        self.assertEqual(target.read_bytes(), b"Retain fictional target")
        self.assertEqual(list(folder.iterdir()), [])

    def direct_dangling_output(self, option):
        self.fixture("a.txt")
        absent = self.work / (option[2:] + "-direct-absent.json")
        output = self.work / (option[2:] + "-direct-link.json")
        self.symlink(output, absent)
        self.run_cli(option, output, expected=2)
        self.assertTrue(output.is_symlink())
        return absent

    def inserted_dangling_output(self, option):
        # Preflight outside main: missing privilege must never become an expected
        # application exit. Actual callback creation errors escape main as assertions.
        preflight = self.work / (option[2:] + "-preflight-link.json")
        self.symlink(preflight, self.work / "unused-owned-preflight-target")
        absent = self.work / (option[2:] + "-inserted-absent.json")
        output = self.work / (option[2:] + "-inserted-link.json")
        script = self.wrapper("""
            selected, absent = Path(OUTPUT_VALUE), Path(ABSENT_VALUE)
            def insert():
                try:
                    selected.symlink_to(absent)
                except OSError as error:
                    raise AssertionError('Native output fixture creation failed') from error
                events.append(True)
            if os.name == 'nt':
                backend = tool._windows()
                original = backend.exclusive_write
                def write(path, data, error):
                    assert Path(path) == selected
                    insert()
                    return original(path, data, error)
                backend.exclusive_write = write
            else:
                original = Path.open
                def opened(path, mode='r', *args, **kwargs):
                    if path == selected and mode == 'x':
                        insert()
                    return original(path, mode, *args, **kwargs)
                Path.open = opened
            """.replace("OUTPUT_VALUE", repr(str(output))).replace("ABSENT_VALUE", repr(str(absent))),
                              postlude="assert events == [True] and status == 2\n")
        self.run_cli(option, output, script=script, expected=2)
        self.addCleanup(output.unlink)
        self.assertTrue(output.is_symlink())
        return absent

    def test_native_dangling_report_output_preserves_targets(self):
        absent = self.direct_dangling_output("--report")
        self.assertFalse(absent.exists())
        absent = self.inserted_dangling_output("--report")
        self.assertFalse(absent.exists())

    def test_native_dangling_write_manifest_output_preserves_targets(self):
        absent = self.direct_dangling_output("--write-manifest")
        self.assertFalse(absent.exists())
        absent = self.inserted_dangling_output("--write-manifest")
        self.assertFalse(absent.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_boundaries_and_entry_review(self):
        self.fixture("a.txt")
        alias = self.work / "root-junction"
        self.junction(alias, self.root)
        self.run_cli(root=alias, expected=2)
        controls = self.work / "owned-controls"
        controls.mkdir()
        (controls / "deny.json").write_bytes(b"[]")
        (controls / "manifest.json").write_bytes(b'{"schema_version":1,"inventory":[]}')
        control_alias = self.work / "controls-junction"
        self.junction(control_alias, controls)
        self.run_cli("--deny-file", control_alias / "deny.json", expected=2)
        self.run_cli("--manifest", control_alias / "manifest.json", expected=2)
        for option in ("--report", "--write-manifest"):
            self.run_cli(option, control_alias / "out.json", expected=2)
        self.assertFalse((controls / "out.json").exists())
        entry = self.root / "entry-junction"
        self.junction(entry, controls)
        result, summary = self.report(expected=1)
        self.assertEqual(summary["findings"], {"LINK_OR_REPARSE": 1})
        self.assertEqual([row["path"] for row in result["findings"]], ["entry-junction"])

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_source_and_control_are_refused(self):
        fifo = self.root / "owned-fifo.txt"
        os.mkfifo(fifo, 0o600)
        result, summary = self.report(expected=1)
        self.assertEqual(summary["findings"], {"NOT_REGULAR": 1})
        self.assertEqual(result["scope"]["bytes_read"], 0)
        self.assertEqual(result["inventory"], [])
        control = self.work / "owned-control-fifo"
        os.mkfifo(control, 0o600)
        for option in ("--deny-file", "--manifest"):
            self.run_cli(option, control, expected=2)

    def test_controlled_entry_total_and_encoded_output_limits_fail_without_false_success(self):
        for name in ("a.txt", "b.txt", "c.txt"):
            self.fixture(name, b"abc\n")
        entry_script = self.wrapper("assert tool.MAX_FILES == 20000\ntool.MAX_FILES = 2\n")
        result, summary = self.report(expected=1, script=entry_script)
        self.assertIn("ENTRY_LIMIT", summary["errors"])
        self.assertEqual(result["scope"]["max_entries"], 2)
        total_script = self.wrapper("assert tool.MAX_TOTAL == 64*1024*1024\ntool.MAX_TOTAL = 8\n")
        result, summary = self.report(expected=1, script=total_script)
        self.assertEqual(summary["findings"], {"SIZE_LIMIT": 1})
        self.assertEqual(result["scope"]["bytes_read"], 8)
        self.assertEqual(len(result["inventory"]), 2)
        if os.name == "nt":
            output = self.work / "over-encoded-budget.json"
            encoded_script = self.wrapper("assert tool.MAX_REPORT == 64*1024*1024\ntool.MAX_REPORT = 32\n")
            self.run_cli("--report", output, script=encoded_script, expected=2)
            self.assertFalse(output.exists())

    def junction(self, link, target):
        from ctypes import wintypes

        self.assertTrue(link.is_relative_to(self.work) and target.is_relative_to(self.work))
        link.mkdir()
        self.addCleanup(link.rmdir)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        kernel.DeviceIoControl.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        substitute = ("\\??\\" + str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute + b"\x00\x00" + printable + b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8 + len(payload), 0,
                           0, len(substitute), len(substitute) + 2, len(printable)) + payload
        handle = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(handle, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
