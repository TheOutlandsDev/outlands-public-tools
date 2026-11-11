"""Actual copied-runtime CLI fixtures; generated private trees and stdlib only."""

import csv
import ctypes
from datetime import datetime, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("source_inventory.py", "inventory_windows.py", "classify_inventory.py")
HEADERS = ["path", "path_escaped", "bytes", "modified_utc", "sha256", "status"]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def decoded_path(row):
    return row["path"][1:] if row["path_escaped"] == "true" else row["path"]


class Download(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="source-inventory-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied runtime"
        self.runtime.mkdir()
        self.runtime_bytes = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            self.runtime_bytes[name] = data
            (self.runtime / name).write_bytes(data)
        self.source = self.work / "FICTIONAL_PRIVATE_ROOT"
        self.output = self.work / "reports"
        self.source.mkdir()
        self.output.mkdir()
        self.authored = {}
        self.serial = 0
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)

    def fresh(self, name="classification"):
        self.serial += 1
        return self.work / (str(self.serial) + "-" + name)

    def file(self, name, data=b"FICTIONAL_BODY_NOT_REPORT\n"):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.authored[path] = data
        return path

    def rules(self, rules=None, case_sensitive=True):
        path = self.fresh("rules.json")
        obj = dict(schema_version="outlands.path_rules.v1", case_sensitive=case_sensitive,
                   rules=rules or [dict(id="python", category="source", kind="suffix", value=".py")])
        path.write_text(json.dumps(obj) + "\n", encoding="utf-8", newline="\n")
        return path

    def process(self, script, *arguments, expected=0, error=None, inputs=()):
        retained = {path: path.read_bytes() for path in (*self.authored, *inputs) if path.is_file()}
        script = self.runtime / script if isinstance(script, str) else script
        result = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script), *map(str, arguments)],
                                cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=35)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        response = json.loads(result.stdout)
        normalized = result.stdout.replace("\\\\", "\\")
        for private in (str(self.work), str(ROOT), "FICTIONAL_PRIVATE_ROOT", "FICTIONAL_BODY_NOT_REPORT"):
            self.assertNotIn(private, normalized)
        if expected:
            self.assertEqual(response["result"], "INCOMPLETE")
            self.assertEqual(set(response), {"result", "error"})
            if error is not None:
                self.assertEqual(response["error"], error)
        for path, data in retained.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual({path.name for path in self.runtime.iterdir()}, set(RUNTIME))
        for name, data in self.runtime_bytes.items():
            self.assertEqual((self.runtime / name).read_bytes(), data)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        return response

    def inventory(self, *options, root=None, output=None, expected=0, error=None, script="source_inventory.py"):
        output = self.output if output is None else output
        response = self.process(script, "--root", self.source if root is None else root,
                                "--output-dir", output, "--label", "fictional", *options,
                                expected=expected, error=error)
        if expected:
            return response
        self.assertEqual(response["result"], "COMPLETE_WITH_EXCLUSIONS")
        self.assertRegex(response["snapshot"], r"^[0-9]{8}T[0-9]{6}Z_fictional_[0-9a-f]{6}$")
        run = output / response["snapshot"]
        summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(response["file_count"], summary["file_count"])
        self.assertEqual(response["skipped"], summary["skipped"])
        self.assertEqual(summary["files_csv_sha256"], sha((run / "files.csv").read_bytes()))
        return run, summary

    def classify(self, run, rules, output=None, expected=0, error=None):
        output = self.fresh() if output is None else output
        response = self.process("classify_inventory.py", "--inventory", run, "--rules", rules,
                                "--output", output, expected=expected, error=error,
                                inputs=(run / "files.csv", run / "summary.json", rules))
        if expected:
            return response
        self.assertEqual(response["result"], "CLASSIFIED_SUPPLIED_ROWS")
        report = json.loads((output / "classification.json").read_text(encoding="utf-8"))
        for key in ("file_count", "unmatched_files", "overlapping_files"):
            self.assertEqual(response[key], report[key])
        return output, report

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as failure:
            if (os.name == "nt" and getattr(failure, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_INVENTORY_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_fictional_inventory_tree_and_classification_end_to_end(self):
        files = {"docs/readme.md": b"Fictional guide.\n", "src/main.py": b"# Fictional source.\n",
                 "notes.txt": b"Fictional note.\n"}
        for name, data in files.items():
            self.file(name, data)
        run, summary = self.inventory("--tree")
        self.assertEqual((summary["file_count"], summary["hashed_file_count"]), (3, 3))
        self.assertEqual(summary["total_bytes"], sum(map(len, files.values())))
        self.assertEqual(summary["coverage"], "selected_regular_files_only")
        rows = read_csv(run / "files.csv")
        self.assertEqual([row["path"] for row in rows], ["docs/readme.md", "notes.txt", "src/main.py"])
        for row in rows:
            self.assertEqual(row["sha256"], sha(files[row["path"]]))
        rules = self.rules([dict(id="docs", category="documentation", kind="prefix", value="docs/"),
                            dict(id="python", category="source", kind="suffix", value=".py")])
        _, report = self.classify(run, rules)
        self.assertEqual((report["file_count"], report["unmatched_files"], report["overlapping_files"]), (3, 1, 0))
        self.assertEqual(report["category_totals"]["source"], {"files": 1, "bytes": len(files["src/main.py"])})

    def test_exact_hashes_utf8_csv_order_sizes_and_utc_metadata(self):
        files = {"z.py": b"z", "A.py": b"alpha\x00", "\u00e9.py": "Fictional \u03bb".encode()}
        for name, data in files.items():
            self.file(name, data)
        run, summary = self.inventory()
        rows = read_csv(run / "files.csv")
        self.assertEqual([row["path"] for row in rows], sorted(files, key=lambda name: (name.casefold(), name)))
        self.assertEqual(summary["top_level_counts"], {name: 1 for name in files})
        for row in rows:
            self.assertEqual(row["sha256"], sha(files[row["path"]]))
            self.assertEqual(row["bytes"], str(len(files[row["path"]])))
            self.assertEqual(datetime.fromisoformat(row["modified_utc"]).utcoffset(), timedelta(0))
            self.assertEqual((row["path_escaped"], row["status"]), ("false", "ok"))

    def test_formula_prefixes_are_escaped_in_inventory_and_classifier_csv(self):
        names = ["=sum.py", "+plus.py", "-minus.py", "@at.py", "'quote.py", "safe.py"]
        for name in names:
            self.file(name)
        run, _ = self.inventory()
        for row in read_csv(run / "files.csv"):
            exact = decoded_path(row)
            self.assertIn(exact, names)
            self.assertEqual(row["path_escaped"], "false" if exact == "safe.py" else "true")
            self.assertEqual(row["path"], exact if exact == "safe.py" else "'" + exact)
        output, report = self.classify(run, self.rules())
        self.assertEqual({row["path"] for row in report["rows"]}, set(names))
        self.assertEqual([(row["path"], row["path_escaped"]) for row in read_csv(output / "classified-paths.csv")],
                         [(row["path"], row["path_escaped"]) for row in read_csv(run / "files.csv")])

    def test_tree_quotes_unicode_and_escapes_bidi_and_supported_controls(self):
        self.file("inside\u202ename.py")
        self.file("\u00e9.py")
        if os.name != "nt":
            self.file('line\n"quoted".py')
            self.file("tab\tname.py")
        run, summary = self.inventory("--tree")
        raw = (run / "tree.txt").read_bytes()
        text = raw.decode("utf-8", errors="strict")
        self.assertIn('"inside\\u202ename.py"', text)
        self.assertNotIn("\u202e", text)
        self.assertIn('"\u00e9.py"', text)
        self.assertEqual(len(text.splitlines()), 2 + summary["tree"]["displayed_entries"])
        if os.name != "nt":
            self.assertIn('line\\n\\"quoted\\".py', text)
            self.assertIn("tab\\tname.py", text)
        self.assertEqual(summary["tree"]["tree_txt_sha256"], sha(raw))

    def test_depth_limits_only_tree_display_and_retains_deep_hash_coverage(self):
        self.file("outer/inner/deep.py", b"Fictional deep bytes")
        run, summary = self.inventory("--tree", "--tree-depth", "1")
        tree = summary["tree"]
        self.assertEqual((tree["entry_count"], tree["displayed_entries"], tree["hidden_by_depth"]), (3, 1, 2))
        self.assertIs(tree["display_complete"], False)
        self.assertEqual(tree["max_display_depth"], 1)
        self.assertIn("[subtree omitted at display depth limit]", (run / "tree.txt").read_text())
        row = read_csv(run / "files.csv")[0]
        self.assertEqual(row["path"], "outer/inner/deep.py")
        self.assertEqual(row["sha256"], sha(b"Fictional deep bytes"))

    def test_default_and_additional_exclusions_are_additive_and_reported(self):
        for name in ("keep.py", ".git/private.py", "Scratch/private.py", "fictional.key", ".env-fictional"):
            self.file(name)
        for options in (("--tree",), ()):
            with self.subTest(tree=bool(options)):
                run, summary = self.inventory(*options, "--exclude-dir", "scratch", "--exclude-dir", "SCRATCH")
                self.assertEqual(summary["file_count"], 1)
                self.assertEqual(summary["skipped"], dict(directories=2, files=2, links=0, nonregular=0))
                self.assertEqual(summary["additional_excluded_directories"], ["scratch"])
                self.assertIn(".git", summary["default_excluded_directories"])
                self.assertIn(".key", summary["default_excluded_suffixes"])
                self.assertEqual([row["path"] for row in read_csv(run / "files.csv")], ["keep.py"])

    def test_empty_default_and_tree_outputs_have_explicit_zero_scope(self):
        run, summary = self.inventory()
        self.assertEqual({p.name for p in run.iterdir()}, {"files.csv", "summary.json"})
        self.assertEqual(summary["file_count"], 0)
        self.assertNotIn("tree", summary)
        (self.source / "empty").mkdir()
        run, summary = self.inventory("--tree")
        self.assertEqual(summary["tree"]["directory_count"], 1)
        self.assertEqual(summary["tree"]["entry_count"], 1)
        self.assertIs(summary["tree"]["display_complete"], True)
        self.assertIn('"empty/"', (run / "tree.txt").read_text())

    def test_classifier_first_match_overlap_casefold_and_literal_rules(self):
        self.file("docs/Readme.MD", b"guide")
        self.file("main.py", b"source")
        self.file("notes.txt", b"note")
        run, _ = self.inventory()
        rules = self.rules([dict(id="docs-first", category="documentation", kind="prefix", value="DOCS/"),
                            dict(id="markdown", category="text", kind="suffix", value=".md"),
                            dict(id="not-glob", category="literal", kind="suffix", value="*.py")], case_sensitive=False)
        _, report = self.classify(run, rules)
        row = report["rows"][0]
        self.assertEqual(row["category"], "documentation")
        self.assertEqual(row["matching_rule_ids"], ["docs-first", "markdown"])
        self.assertIs(row["overlap"], True)
        self.assertEqual((report["overlapping_files"], report["unmatched_files"]), (1, 2))
        self.assertEqual(report["selection"], "first_matching_rule")
        self.assertEqual(report["comparisons"], 9)
        self.assertIsNone(report["rows"][1]["category"])

    def test_classifier_manifest_and_three_input_snapshot_hashes(self):
        self.file("one.py")
        run, _ = self.inventory("--tree")
        rules = self.rules()
        output, report = self.classify(run, rules)
        self.assertEqual({p.name for p in output.iterdir()}, {"classification.json", "classified-paths.csv", "MANIFEST.json"})
        manifest = json.loads((output / "MANIFEST.json").read_text())
        self.assertEqual(manifest["schema_version"], "outlands.classification_manifest.v1")
        self.assertEqual([row["path"] for row in manifest["files"]], ["classification.json", "classified-paths.csv"])
        for row in manifest["files"]:
            raw = (output / row["path"]).read_bytes()
            self.assertEqual((row["bytes"], row["sha256"]), (len(raw), sha(raw)))
        self.assertEqual(report["inputs"], dict(files_csv_sha256=sha((run / "files.csv").read_bytes()),
                                              summary_json_sha256=sha((run / "summary.json").read_bytes()),
                                              rules_json_sha256=sha(rules.read_bytes())))

    def test_classifier_uses_captured_rows_after_original_source_is_removed(self):
        selected = self.file("one.py")
        run, _ = self.inventory()
        selected.unlink()
        _, report = self.classify(run, self.rules())
        self.assertEqual(report["file_count"], 1)
        self.assertEqual(report["rows"][0]["path"], "one.py")
        self.assertFalse(selected.exists())

    def test_repeated_runs_are_fresh_and_preserve_prior_reports_and_runtime(self):
        self.file("one.py")
        first, _ = self.inventory("--tree")
        retained = {path.name: path.read_bytes() for path in first.iterdir()}
        second, _ = self.inventory("--tree")
        self.assertNotEqual(first, second)
        self.assertEqual(retained, {path.name: path.read_bytes() for path in first.iterdir()})
        self.assertEqual((first / "files.csv").read_bytes(), (second / "files.csv").read_bytes())
        self.assertEqual((first / "tree.txt").read_bytes(), (second / "tree.txt").read_bytes())
        self.assertEqual({p.name for p in self.runtime.iterdir()}, set(RUNTIME))

    def test_classifier_never_overwrites_or_overlaps_inputs_or_makes_parents(self):
        self.file("one.py")
        run, _ = self.inventory()
        rules = self.rules()
        output, _ = self.classify(run, rules)
        retained = {path.name: path.read_bytes() for path in output.iterdir()}
        self.classify(run, rules, output=output, expected=2, error="OUTPUT_EXISTS")
        self.assertEqual(retained, {path.name: path.read_bytes() for path in output.iterdir()})
        self.classify(run, rules, output=run / "new", expected=2, error="OUTPUT_OVERLAPS_INPUT")
        self.classify(run, rules, output=rules, expected=2, error="OUTPUT_OVERLAPS_INPUT")
        absent = self.fresh("absent")
        self.classify(run, rules, output=absent / "new", expected=2)
        self.assertFalse(absent.exists())

    def test_inventory_refuses_output_inside_root_and_requires_existing_parent(self):
        self.file("one.py")
        self.inventory(root=self.source, output=self.source, expected=2, error="OUTPUT_INSIDE_INPUT")
        nested = self.source / "reports"
        nested.mkdir()
        self.inventory(output=nested, expected=2, error="OUTPUT_INSIDE_INPUT")
        absent = self.fresh("absent")
        self.inventory(output=absent, expected=2)
        self.assertFalse(absent.exists())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_malformed_rules_are_fixed_errors_before_output_creation(self):
        self.file("one.py")
        run, _ = self.inventory()
        good = json.loads(self.rules().read_text())
        unsupported = json.loads(json.dumps(good))
        unsupported["rules"][0]["kind"] = "regex"
        duplicate = b'{"schema_version":"outlands.path_rules.v1","case_sensitive":true,"case_sensitive":false,"rules":[]}'
        for data, code in ((b"{broken", "INVALID_JSON"), (b"\xff", "INVALID_JSON"),
                           (duplicate, "JSON_DUPLICATE_KEY"), (json.dumps(unsupported).encode(), "RULE_KIND_UNSUPPORTED")):
            with self.subTest(code=code):
                rules = self.fresh("invalid-rules.json")
                rules.write_bytes(data)
                output = self.fresh()
                self.classify(run, rules, output=output, expected=2, error=code)
                self.assertFalse(output.exists())

    def test_csv_hash_mismatch_and_inconsistent_summary_totals_are_refused(self):
        self.file("one.py")
        run, summary = self.inventory()
        rules = self.rules()
        raw = (run / "files.csv").read_bytes()
        (run / "files.csv").write_bytes(raw + b"\n")
        self.classify(run, rules, expected=2, error="CSV_HASH_MISMATCH")
        (run / "files.csv").write_bytes(raw)
        summary["total_bytes"] += 1
        (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        self.classify(run, rules, expected=2, error="INVENTORY_TOTALS_MISMATCH")

    def test_strict_csv_headers_quoting_utf8_duplicates_and_escaping(self):
        self.file("one.py")
        run, summary = self.inventory()
        rules = self.rules()
        raw = (run / "files.csv").read_bytes()
        row = read_csv(run / "files.csv")[0]
        def csv_bytes(rows):
            handle = io.StringIO(newline="")
            writer = csv.DictWriter(handle, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerows(rows)
            return handle.getvalue().encode()
        bad_escape = dict(row, path_escaped="true")
        for data, code in ((b"wrong\n", "CSV_HEADER_INVALID"), (b"\xff", "CSV_INVALID"),
                           (",".join(HEADERS).encode() + b'\n"unterminated', "CSV_INVALID"),
                           (csv_bytes([row, row]), "CSV_PATH_DUPLICATE"),
                           (csv_bytes([bad_escape]), "CSV_ESCAPE_INVALID")):
            with self.subTest(code=code):
                (run / "files.csv").write_bytes(data)
                summary["files_csv_sha256"] = sha(data)
                (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
                self.classify(run, rules, expected=2, error=code)
        self.assertNotEqual(raw, (run / "files.csv").read_bytes())

    def test_classifier_read_byte_limits_apply_to_each_selected_input(self):
        self.file("one.py")
        run, _ = self.inventory()
        rules = self.rules()
        for path, maximum in ((run / "files.csv", 16 * 1024 * 1024),
                              (run / "summary.json", 1024 * 1024), (rules, 256 * 1024)):
            with self.subTest(input=path.name):
                retained = path.read_bytes()
                with path.open("wb") as handle:
                    handle.truncate(maximum + 1)
                output = self.fresh()
                self.classify(run, rules, output=output, expected=2, error="INPUT_BYTE_LIMIT")
                self.assertFalse(output.exists())
                path.write_bytes(retained)

    def test_inventory_file_count_and_byte_limits_fail_before_reports(self):
        self.file("one.py", b"1234")
        self.file("two.py", b"5678")
        for options, code in ((("--max-files", "1"), "FILE_COUNT_LIMIT"),
                              (("--max-file-bytes", "3"), "FILE_BYTE_LIMIT"),
                              (("--max-total-bytes", "7"), "TOTAL_BYTE_LIMIT"),
                              (("--max-files", "0"), "INVALID_LIMIT")):
            with self.subTest(code=code):
                self.inventory(*options, expected=2, error=code)
                self.assertEqual(list(self.output.iterdir()), [])

    def test_no_implicit_defaults_and_invalid_options_create_no_reports(self):
        self.file("one.py")
        self.process("source_inventory.py", expected=2, error="ARGUMENTS_INVALID")
        self.process("classify_inventory.py", expected=2, error="ARGUMENTS_INVALID")
        self.inventory("--tree-depth", "1", expected=2, error="TREE_REQUIRED")
        self.inventory("--tree", "--tree-depth", "65", expected=2, error="INVALID_TREE_OPTIONS")
        self.inventory("--exclude-dir", "../fictional", expected=2, error="INVALID_EXCLUSIONS")
        self.inventory("--unknown", expected=2, error="ARGUMENTS_INVALID")
        self.assertEqual(list(self.output.iterdir()), [])

    def test_classifier_absolute_paths_and_supported_summary_contract_are_required(self):
        self.file("one.py")
        run, summary = self.inventory()
        rules = self.rules()
        self.process("classify_inventory.py", "--inventory", run.relative_to(self.work),
                     "--rules", rules, "--output", self.fresh(), expected=2, error="ABSOLUTE_PATH_REQUIRED")
        summary["fictional_unknown"] = True
        (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        self.classify(run, rules, expected=2, error="JSON_FIELDS_INVALID")

    def test_controlled_child_late_failure_does_not_certify_complete_looking_summary(self):
        self.file("one.py")
        wrapper = self.fresh("controlled-child.py")
        wrapper.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0, " + repr(str(self.runtime)) + ")\n"
                           "import source_inventory as tool\noriginal = tool._exclusive_write\n"
                           "def late(path, data):\n    original(path, data)\n"
                           "    if path.name == 'summary.json':\n        raise tool.InventoryError('CONTROLLED_LATE_FAILURE')\n"
                           "tool._exclusive_write = late\nraise SystemExit(tool.main(sys.argv[1:]))\n", encoding="utf-8")
        self.inventory(script=wrapper, expected=2, error="CONTROLLED_LATE_FAILURE")
        runs = list(self.output.iterdir())
        self.assertEqual(len(runs), 1)
        summary = json.loads((runs[0] / "summary.json").read_text())
        self.assertEqual(summary["file_count"], 1)
        self.assertEqual(summary["files_csv_sha256"], sha((runs[0] / "files.csv").read_bytes()))

    def test_native_symlink_root_is_refused(self):
        self.file("one.py")
        link = self.work / "linked source"
        self.symlink(link, self.source, directory=True)
        self.inventory(root=link, expected=2, error="LINKED_PATH")
        self.assertEqual(list(self.output.iterdir()), [])

    def test_native_symlink_output_parent_is_refused(self):
        self.file("one.py")
        run, _ = self.inventory()
        target = self.work / "real linked output"
        target.mkdir()
        link = self.work / "linked output"
        self.symlink(link, target, directory=True)
        self.inventory(output=link, expected=2, error="LINKED_PATH")
        self.classify(run, self.rules(), output=link / "new", expected=2, error="UNSUPPORTED_OR_LINKED_PATH")
        self.assertEqual(list(target.iterdir()), [])

    def test_native_entry_links_are_skipped_and_counted(self):
        self.file("one.py")
        external = self.work / "external fictional bytes.py"
        external.write_bytes(b"Fictional external body")
        directory = self.work / "external fictional directory"
        directory.mkdir()
        (directory / "not-followed.py").write_bytes(b"Fictional not selected")
        self.symlink(self.source / "file-link.py", external)
        self.symlink(self.source / "dir-link", directory, directory=True)
        run, summary = self.inventory("--tree")
        self.assertEqual(summary["skipped"], dict(directories=0, files=0, links=2, nonregular=0))
        self.assertEqual(summary["file_count"], 1)
        self.assertEqual(summary["tree"]["entry_count"], 1)
        self.assertEqual([row["path"] for row in read_csv(run / "files.csv")], ["one.py"])
        self.assertNotIn("link", (run / "tree.txt").read_text())
        self.assertEqual(external.read_bytes(), b"Fictional external body")

    def test_native_classifier_linked_inputs_and_output_are_refused(self):
        self.file("one.py")
        run, _ = self.inventory()
        rules = self.rules()
        link = self.fresh("rules-link.json")
        self.symlink(link, rules)
        self.classify(run, link, expected=2, error="UNSUPPORTED_OR_LINKED_PATH")
        run_link = self.fresh("run-link")
        self.symlink(run_link, run, directory=True)
        self.classify(run_link, rules, expected=2, error="UNSUPPORTED_OR_LINKED_PATH")
        target = self.fresh("retained-output")
        target.mkdir()
        (target / "retained.txt").write_bytes(b"Fictional retained bytes")
        out_link = self.fresh("output-link")
        self.symlink(out_link, target, directory=True)
        self.classify(run, rules, output=out_link, expected=2, error="OUTPUT_EXISTS")
        self.assertEqual((target / "retained.txt").read_bytes(), b"Fictional retained bytes")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_boundaries_and_entry_skip(self):
        from ctypes import wintypes

        self.file("one.py")
        target = self.work / "junction target"
        target.mkdir()
        (target / "not-followed.py").write_bytes(b"Fictional target")
        link = self.source / "junction entry"
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
        self.inventory(root=link, expected=2, error="LINKED_PATH")
        self.inventory(output=link, expected=2, error="LINKED_PATH")
        run, summary = self.inventory("--tree")
        self.assertEqual(summary["file_count"], 1)
        self.assertEqual(summary["skipped"]["links"], 1)
        self.assertNotIn("junction", (run / "tree.txt").read_text())
        self.classify(run, self.rules(), output=link / "new", expected=2, error="UNSUPPORTED_OR_LINKED_PATH")
        self.assertEqual(sorted(path.name for path in target.iterdir()), ["not-followed.py"])


if __name__ == "__main__":
    unittest.main()
