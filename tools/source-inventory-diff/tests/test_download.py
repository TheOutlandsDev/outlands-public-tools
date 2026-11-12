"""Fresh single-script CLI checks using independently authored report metadata."""

import csv
import ctypes
from datetime import datetime
import hashlib
import importlib.metadata
import io
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
STAMP = "2030-01-01T00:00:00+00:00"
HEADERS = ["path", "path_escaped", "bytes", "modified_utc", "sha256", "status"]
FLAGS = dict.fromkeys(("roots_scanned", "inventoried_files_opened", "files_modified", "files_deleted",
                      "renames_verified", "canonical_copy_selected", "authenticity_verified",
                      "scope_equivalence_verified", "tree_metadata_compared", "network_probed"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path="example.txt", *, size=7, digest=None, stamp=STAMP):
    return dict(path=path, bytes=size, sha256=digest or sha(("Fictional declaration: " + path).encode("utf-8")),
                modified_utc=stamp)


def csv_bytes(records):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    for row in records:
        name = row["path"]
        escape = name.startswith(("'", "\t", "\r", "\n")) or name.lstrip().startswith(("=", "+", "-", "@"))
        writer.writerow(["'" + name if escape else name, "true" if escape else "false", row["bytes"],
                         row["modified_utc"], row["sha256"], "ok"])
    return output.getvalue().encode("utf-8")


def summary_for(records, raw):
    top = {}
    for row in records:
        key = row["path"].split("/", 1)[0]
        top[key] = top.get(key, 0) + 1
    return dict(schema_version="outlands.source_inventory.v1", label="fictional", created_at_utc=STAMP,
                coverage="selected_regular_files_only", file_count=len(records), hashed_file_count=len(records),
                total_bytes=sum(row["bytes"] for row in records), top_level_counts=top,
                skipped=dict(directories=0, files=0, links=0, nonregular=0), files_csv_sha256=sha(raw).upper(),
                path_encoding="Remove one leading apostrophe only when path_escaped is true.",
                limits=dict(max_files=10000, max_file_bytes=67108864, max_total_bytes=268435456, max_entries=10000),
                default_excluded_directories=[".git"], default_excluded_suffixes=[".log"])


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="inventory-diff-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "inventory_diff.py"
        self.source.write_bytes((ROOT / "inventory_diff.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def run_fixture(self, records=(), **changes):
        self.serial += 1
        folder = self.work / ("FICTIONAL_PRIVATE_RUN_" + str(self.serial))
        folder.mkdir()
        rows = [dict(row) for row in records]
        raw = csv_bytes(rows)
        data = summary_for(rows, raw)
        data.update(changes)
        selected = dict(folder=folder, records=rows, csv=raw, data=data)
        return self.rewrite(selected)

    def rewrite(self, run, *, raw=None, summary=None):
        if raw is not None:
            run["csv"] = raw
            run["data"]["files_csv_sha256"] = sha(raw)
        run["summary"] = json.dumps(run["data"], ensure_ascii=True).encode("utf-8") if summary is None else summary
        (run["folder"] / "files.csv").write_bytes(run["csv"])
        (run["folder"] / "summary.json").write_bytes(run["summary"])
        return run

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import inventory_diff as tool\nevents = []\n" + textwrap.dedent(body)
                          + "\nstatus = tool.main(sys.argv[1:])\n" + textwrap.dedent(postlude)
                          + "\nraise SystemExit(status)\n", encoding="utf-8", newline="\n")
        return script

    def process(self, *arguments, expected=0, code=None, script=None, json_output=True):
        tree = {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")}
        retained = {}
        for path in self.work.rglob("*"):
            if not path.is_symlink() and not path.is_junction():
                info = path.lstat()
                if stat.S_ISREG(info.st_mode):
                    retained[path] = (sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
        done = subprocess.run([sys.executable, "-B", "-s", "-X", "utf8", str(script or self.source), *map(str, arguments)],
                              cwd=self.work, env=self.environment, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=90)
        self.assertEqual(done.returncode, expected, done.stdout[:2000] + done.stderr)
        self.assertEqual(done.stderr, "")
        self.assertEqual(tree, {path.relative_to(self.work).as_posix() for path in self.work.rglob("*")})
        for path, before in retained.items():
            info = path.lstat()
            self.assertEqual((sha(path.read_bytes()), info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink), before)
        self.assertEqual(list(self.runtime.iterdir()), [self.source])
        self.assertEqual(sha(self.source.read_bytes()), self.runtime_hash)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
        self.assertNotIn(str(self.work), done.stdout.replace("\\\\", "\\"))
        self.assertNotIn("FICTIONAL_PRIVATE", done.stdout)
        if not json_output:
            return done.stdout
        self.assertEqual(len(done.stdout.splitlines()), 1)
        value = json.loads(done.stdout)
        if expected in (2, 130):
            self.assertEqual(value, dict(status="ERROR", code=code or "INTERRUPTED", **FLAGS))
        else:
            self.assertTrue(all(value[key] is False for key in FLAGS))
        return value

    def run_cli(self, before, after=None, **options):
        return self.process("--before", before["folder"], "--after", (after or before)["folder"], **options)

    def golden(self, before, after, kinds, *, issues=(), coverage_issues=(), ambiguities=(), groups=(), conflicts=()):
        old = {row["path"]: row for row in before["records"]}
        new = {row["path"]: row for row in after["records"]}
        counts = dict(only_in_before=0, only_in_after=0, hash_or_size_changed=0, mtime_only_changed=0, unchanged=0)
        rows = []
        for path, kind in kinds:
            counts[kind.lower()] += 1
            sides = {}
            for name, records in (("before", old), ("after", new)):
                row = records.get(path)
                sides[name] = None if row is None else dict(bytes=row["bytes"], sha256=row["sha256"].lower(),
                                                            modified_utc=datetime.fromisoformat(row["modified_utc"]).isoformat())
            rows.append(dict(path=path, classification=kind, **sides))
        status = "REVIEW_REQUIRED" if issues else "DIFFERENCES_REPORTED" if any(kind != "UNCHANGED" for path, kind in kinds) else "MATCHING_SELECTED_RECORDS"
        return dict(schema_version="outlands.inventory_diff.v1", status=status,
                    scope="SUPPLIED_SELECTED_REGULAR_FILE_RECORDS_ONLY", **FLAGS,
                    counts=dict(before=len(old), after=len(new), **counts), issues=list(issues),
                    coverage=dict(declarations_match=not coverage_issues, issues=list(coverage_issues),
                                  skipped_before=before["data"]["skipped"], skipped_after=after["data"]["skipped"]),
                    input_hashes={side: dict(files_csv_sha256=sha(run["csv"]), summary_json_sha256=sha(run["summary"]))
                                  for side, run in (("before", before), ("after", after))},
                    rows=rows, casefold_ambiguities=list(ambiguities), hash_size_groups=list(groups),
                    digest_size_conflicts=list(conflicts))

    def compare(self, before, after=None, kinds=None, **changes):
        after = after or before
        if kinds is None:
            kinds = [(row["path"], "UNCHANGED") for row in sorted(before["records"], key=lambda row: (row["path"].casefold(), row["path"]))]
        wanted = self.golden(before, after, kinds, **changes)
        self.assertEqual(self.run_cli(before, after, expected=int(wanted["status"] != "MATCHING_SELECTED_RECORDS")), wanted)
        return wanted

    def symlink(self, path, target, directory=False):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_INVENTORY_DIFF_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_matching_empty_and_nonempty_reports_have_complete_golden_json(self):
        self.compare(self.run_fixture())
        run = self.run_fixture([record("z.txt"), record("nested/a.py")])
        self.compare(run)
        self.assertEqual({path.name for path in run["folder"].iterdir()}, {"files.csv", "summary.json"})

    def test_all_five_record_classifications_have_exact_metadata_and_counts(self):
        old = [record("gone.txt"), record("hash.txt"), record("time.txt"), record("unchanged.txt")]
        new = [record("added.txt"), record("hash.txt", digest=sha(b"Fictional changed declaration")),
               record("time.txt", stamp="2031-01-01T00:00:00Z"), record("unchanged.txt")]
        self.compare(self.run_fixture(old), self.run_fixture(new),
                     [("added.txt", "ONLY_IN_AFTER"), ("gone.txt", "ONLY_IN_BEFORE"), ("hash.txt", "HASH_OR_SIZE_CHANGED"),
                      ("time.txt", "MTIME_ONLY_CHANGED"), ("unchanged.txt", "UNCHANGED")])

    def test_reversed_comparison_swaps_sides_without_inventing_source_changes(self):
        before, after = self.run_fixture([record("old.txt")]), self.run_fixture([record("new.txt")])
        self.compare(before, after, [("new.txt", "ONLY_IN_AFTER"), ("old.txt", "ONLY_IN_BEFORE")])
        self.compare(after, before, [("new.txt", "ONLY_IN_BEFORE"), ("old.txt", "ONLY_IN_AFTER")])

    def test_hash_size_groups_preserve_many_to_many_hints_without_rename_claims(self):
        digest = sha(b"Fictional common declared digest")
        before = self.run_fixture([record("a.txt", digest=digest), record("b.txt", digest=digest)])
        after = self.run_fixture([record("c.txt", digest=digest), record("d.txt", digest=digest)])
        group = dict(sha256=digest, bytes=7, before_paths=["a.txt", "b.txt"], after_paths=["c.txt", "d.txt"])
        value = self.compare(before, after, [(name, kind) for name, kind in
                                             (("a.txt", "ONLY_IN_BEFORE"), ("b.txt", "ONLY_IN_BEFORE"),
                                              ("c.txt", "ONLY_IN_AFTER"), ("d.txt", "ONLY_IN_AFTER"))],
                             issues=["HASH_SIZE_GROUP_HINTS_PRESENT"], groups=[group])
        self.assertFalse(value["renames_verified"] or value["canonical_copy_selected"])

    def test_casefold_ambiguities_keep_exact_names_and_do_not_normalize_unicode(self):
        run = self.run_fixture([record("Straße.txt"), record("STRASSE.txt")])
        self.compare(run, kinds=[("STRASSE.txt", "UNCHANGED"), ("Straße.txt", "UNCHANGED")],
                     issues=["CASEFOLD_PATH_AMBIGUITY"],
                     ambiguities=[dict(before_paths=["STRASSE.txt", "Straße.txt"], after_paths=["STRASSE.txt", "Straße.txt"])])
        self.compare(self.run_fixture([record("é.txt")]), self.run_fixture([record("e\u0301.txt")]),
                     [("e\u0301.txt", "ONLY_IN_AFTER"), ("é.txt", "ONLY_IN_BEFORE")])

    def test_same_digest_different_declared_sizes_is_a_separate_review_conflict(self):
        digest = sha(b"Fictional conflicting declared sizes")
        self.compare(self.run_fixture([record("a.txt", size=5, digest=digest)]),
                     self.run_fixture([record("a.txt", size=6, digest=digest)]), [("a.txt", "HASH_OR_SIZE_CHANGED")],
                     issues=["DIGEST_SIZE_CONFLICT"], conflicts=[dict(sha256=digest, reported_sizes=[5, 6])])

    def test_coverage_sets_limits_and_skips_have_exact_ordered_review_codes(self):
        rows = [record()]
        left = self.run_fixture(rows, default_excluded_directories=[".git", "CACHE"], additional_excluded_directories=["private"])
        right = self.run_fixture(rows, default_excluded_directories=["PRIVATE", ".GIT"], additional_excluded_directories=["cache", "cache"])
        self.compare(left, right)
        left["data"]["skipped"]["links"] = 1
        right["data"]["skipped"]["nonregular"] = 2
        right["data"]["default_excluded_directories"] = [".git", "different"]
        right["data"]["additional_excluded_directories"] = []
        right["data"]["default_excluded_suffixes"] = [".tmp"]
        right["data"]["limits"]["max_file_bytes"] -= 1
        self.rewrite(left)
        self.rewrite(right)
        coverage = ["DIRECTORY_EXCLUSIONS_DIFFER", "SUFFIX_EXCLUSIONS_DIFFER", "LIMITS_DIFFER"]
        self.compare(left, right, issues=coverage + ["SKIPPED_ENTRIES_PRESENT"], coverage_issues=coverage)

    def test_capture_labels_tree_row_order_digest_case_and_utc_spelling_do_not_change_records(self):
        rows = [record("z.txt"), record("a.txt")]
        left = self.run_fixture(rows, label="capture_before", tree={"uninterpreted": ["fictional"]})
        changed = [dict(row, sha256=row["sha256"].upper(), modified_utc="2030-01-01T00:00:00Z") for row in reversed(rows)]
        right = self.run_fixture(changed, label="capture_after", created_at_utc="2032-01-01T00:00:00Z", tree={"different": True})
        self.compare(left, right)

    def test_csv_formula_escapes_quoted_controls_unicode_and_backslashes_remain_data(self):
        names = ["=sum(1,2).txt", "+formula.txt", "  @formula.txt", "'literal.txt", "\tcontrol.txt",
                 "line\nname.txt", 'quoted"name.txt', "folder/back\\slash.txt", "unicode/雪.txt"]
        self.compare(self.run_fixture([record(name) for name in names]))

    def test_csv_headers_rows_escaping_sizes_hashes_and_timestamps_are_strict(self):
        base = self.run_fixture([record()])
        good = list(csv.reader(io.StringIO(base["csv"].decode(), newline="")))
        changes = [(0, 0, "other", "CSV_HEADER_INVALID"), (1, 1, "TRUE", "CSV_PATH_INVALID"),
                   (1, 0, "=formula", "CSV_ESCAPE_INVALID"), (1, 0, "../escape", "CSV_PATH_INVALID"),
                   (1, 2, "01", "CSV_BYTES_INVALID"), (1, 2, "-1", "CSV_BYTES_INVALID"),
                   (1, 4, "not-a-hash", "CSV_ROW_INVALID"), (1, 5, "skipped", "CSV_ROW_INVALID"),
                   (1, 3, "2030-01-01T00:00:00", "CSV_ROW_INVALID")]
        for row, column, replacement, code in changes:
            with self.subTest(code=code, column=column):
                fields = [list(item) for item in good]
                fields[row][column] = replacement
                out = io.StringIO(newline="")
                csv.writer(out).writerows(fields)
                self.rewrite(base, raw=out.getvalue().encode())
                self.run_cli(base, expected=2, code=code)
        for raw, code in ((b"\xff", "CSV_INVALID"), (b"\xef\xbb\xbf" + csv_bytes([record()]), "CSV_HEADER_INVALID"),
                          (csv_bytes([record(), record()]), "CSV_PATH_DUPLICATE"),
                          (csv_bytes([]) + b'"unterminated', "CSV_INVALID")):
            self.rewrite(base, raw=raw)
            self.run_cli(base, expected=2, code=code)

    def test_json_duplicates_numbers_bom_utf8_and_unknown_fields_are_strict(self):
        run = self.run_fixture()
        raw = run["summary"]
        cases = [(b"\xff", "INVALID_JSON"), (b"\xef\xbb\xbf" + raw, "INVALID_JSON"),
                 (b"[]", "JSON_OBJECT_REQUIRED"), (b"{", "INVALID_JSON"),
                 (raw[:-1] + b',"label":"again"}', "JSON_DUPLICATE_KEY")]
        for token in (b"1.0", b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            cases.append((raw.replace(b'"file_count": 0', b'"file_count": ' + token), "JSON_INTEGER_REQUIRED"))
        for value, code in cases:
            self.rewrite(run, summary=value)
            self.run_cli(run, expected=2, code=code)
        run["data"]["unknown"] = "FICTIONAL_PRIVATE_UNKNOWN"
        self.rewrite(run)
        self.run_cli(run, expected=2, code="JSON_FIELDS_INVALID")

    def test_summary_hash_counts_top_levels_types_and_declarations_are_validated(self):
        cases = [("files_csv_sha256", "0"*64, "CSV_HASH_MISMATCH"),
                 ("schema_version", "other", "INVENTORY_SCHEMA_UNSUPPORTED"),
                 ("file_count", True, "INVENTORY_TOTALS_INVALID"),
                 ("hashed_file_count", False, "INVENTORY_TOTALS_INVALID"),
                 ("total_bytes", 8, "INVENTORY_TOTALS_MISMATCH"),
                 ("top_level_counts", {}, "INVENTORY_TOTALS_MISMATCH"),
                 ("label", "FICTIONAL_PRIVATE_LABEL", "INVENTORY_METADATA_INVALID"),
                 ("created_at_utc", "2030-01-01", "INVENTORY_METADATA_INVALID"),
                 ("skipped", dict(directories=False, files=0, links=0, nonregular=0), "INVENTORY_METADATA_INVALID")]
        for field, value, code in cases:
            with self.subTest(field=field):
                run = self.run_fixture([record()], **{field: value})
                self.run_cli(run, expected=2, code=code)

    def wide_records(self, prefix, target_bytes=16*1024*1024):
        rows = [record(prefix + "/" + str(index).zfill(4) + "/x", size=1) for index in range(4096)]
        needed = target_bytes - len(csv_bytes(rows))
        each, extra = divmod(needed, len(rows))
        for index, row in enumerate(rows):
            row["path"] += "x"*(each + (index < extra))
        raw = csv_bytes(rows)
        self.assertEqual(len(raw), target_bytes)
        self.assertLessEqual(max(map(lambda row: len(row["path"]), rows)), 4096)
        return rows

    def test_actual_csv_sixteen_mib_and_json_one_mib_exact_and_over_limits(self):
        run = self.run_fixture(self.wide_records("wide"))
        self.compare(run)
        self.rewrite(run, raw=run["csv"] + b" ")
        self.run_cli(run, expected=2, code="INPUT_BYTE_LIMIT")
        run = self.run_fixture()
        self.rewrite(run, summary=run["summary"] + b" "*(1024*1024-len(run["summary"])))
        self.compare(run)
        self.rewrite(run, summary=run["summary"] + b" ")
        self.run_cli(run, expected=2, code="INPUT_BYTE_LIMIT")

    def test_ten_thousand_rows_and_four_thousand_ninety_six_character_paths(self):
        rows = [record("bucket/item-" + str(index), size=1) for index in range(10000)]
        run = self.run_fixture(rows)
        self.compare(run)
        self.rewrite(run, raw=csv_bytes(rows + [record("bucket/extra", size=1)]))
        self.run_cli(run, expected=2, code="CSV_ROWS_INVALID")
        name = "bucket/" + "x"*(4096-7)
        self.compare(self.run_fixture([record(name)]))
        self.run_cli(self.run_fixture([record(name + "x")]), expected=2, code="CSV_PATH_INVALID")

    def test_json_depth_node_string_and_unicode_scalar_limits_are_bounded(self):
        for depth in (15, 16):
            tree = 0
            for index in range(depth):
                tree = {"child": tree}
            run = self.run_fixture(tree=tree)
            if depth == 15:
                self.compare(run)
            else:
                self.run_cli(run, expected=2, code="JSON_STRUCTURE_LIMIT")
        run = self.run_fixture()
        def nodes(value):
            if isinstance(value, dict):
                return 1 + sum(nodes(item) for item in value.values())
            if isinstance(value, list):
                return 1 + sum(map(nodes, value))
            return 1
        count = 50000 - nodes(run["data"]) - 2
        run["data"]["tree"] = {"items": [0]*count}
        self.rewrite(run)
        self.compare(run)
        run["data"]["tree"]["items"].append(0)
        self.rewrite(run)
        self.run_cli(run, expected=2, code="JSON_STRUCTURE_LIMIT")
        self.compare(self.run_fixture(tree={"value": "x"*4096}))
        self.run_cli(self.run_fixture(tree={"value": "x"*4097}), expected=2, code="JSON_STRING_LIMIT")
        self.run_cli(self.run_fixture(tree={"value": "\ud800"}), expected=2, code="INVALID_JSON_TEXT")

    def test_serialized_stdout_budget_refuses_whole_report_before_printing(self):
        before = self.run_fixture(self.wide_records("old"))
        after = self.run_fixture(self.wide_records("new"))
        self.run_cli(before, after, expected=2, code="OUTPUT_BYTE_LIMIT")
        run = self.run_fixture([record()])
        wanted = self.golden(run, run, [("example.txt", "UNCHANGED")])
        size = len(json.dumps(wanted, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        for limit in (size, size-1):
            script = self.wrapper("assert tool.MAX_OUTPUT_BYTES == 32*1024*1024\ntool.MAX_OUTPUT_BYTES = " + str(limit) + "\n")
            value = self.run_cli(run, script=script, expected=0 if limit == size else 2,
                                 code=None if limit == size else "OUTPUT_BYTE_LIMIT")
            if limit == size:
                self.assertEqual(value, wanted)

    def test_help_version_explicit_arguments_and_ambiguous_path_forms(self):
        self.assertIn("--before", self.process("--help", json_output=False))
        self.assertEqual(self.process("--version", json_output=False), "source-inventory-diff 0.1.0\n")
        for args in ((), ("--before", "FICTIONAL_PRIVATE_MISSING"), ("--bef", "x", "--after", "y")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        run = self.run_fixture()
        for value in (str(run["folder"]) + ".", str(run["folder"]) + " ", str(self.work / "CON"),
                      str(self.work / "a:stream"), str(self.work / ".." / "escape")):
            self.process("--before", value, "--after", run["folder"], expected=2, code="INPUT_PATH_INVALID")
        self.assertEqual(self.process("--before", run["folder"].name, "--after", run["folder"].name),
                         self.golden(run, run, []))

    def test_native_hardlinked_csv_and_summary_controls_are_refused(self):
        for name in ("files.csv", "summary.json"):
            run = self.run_fixture()
            original = run["folder"] / name
            alias = self.work / ("owned-hardlink-" + name)
            os.link(original, alias)
            self.assertGreaterEqual(original.stat().st_nlink, 2)
            self.run_cli(run, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_controlled_interrupt_read_and_final_identity_recheck_release_handles(self):
        run = self.run_fixture([record()])
        interrupted = self.wrapper("""
            original = os.fdopen
            descriptors = []
            class Interrupted:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    self.stream.__enter__()
                    return self
                def __exit__(self, *args):
                    return self.stream.__exit__(*args)
                def fileno(self):
                    return self.stream.fileno()
                def read(self, maximum):
                    events.append(maximum)
                    raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
            def opened(fd, *args, **kwargs):
                descriptors.append(fd)
                return Interrupted(original(fd, *args, **kwargs))
            os.fdopen = opened
            """, postlude="""
            assert status == 130 and len(events) == 1
            for fd in descriptors:
                try:
                    os.fstat(fd)
                except OSError as error:
                    assert error.errno == 9
                else:
                    raise AssertionError('Owned input descriptor remained open')
            """)
        self.run_cli(run, script=interrupted, expected=130)
        changed = self.wrapper("""
            original = tool._fingerprint
            def fingerprint(path):
                events.append(True)
                return ('observed controlled identity change', original(path))
            tool._fingerprint = fingerprint
            """, postlude="assert events == [True] and status == 2\n")
        self.run_cli(run, script=changed, expected=2, code="INPUT_CHANGED")

    def test_native_symlink_run_root_is_refused(self):
        run = self.run_fixture()
        alias = self.work / "linked-run"
        self.symlink(alias, run["folder"], directory=True)
        self.process("--before", alias, "--after", run["folder"], expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_native_symlink_control_leaf_parent_and_dangling_are_refused(self):
        run = self.run_fixture()
        target = self.work / "owned-summary-target.json"
        leaf = run["folder"] / "summary.json"
        leaf.rename(target)
        self.symlink(leaf, target)
        self.run_cli(run, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        dangling = self.run_fixture()
        leaf = dangling["folder"] / "files.csv"
        leaf.unlink()
        absent = self.work / "owned-absent-csv-target"
        self.symlink(leaf, absent)
        self.run_cli(dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        self.assertFalse(absent.exists())
        real = self.work / "owned-run-parent"
        real.mkdir()
        moved = real / "run"
        run2 = self.run_fixture()
        run2["folder"].rename(moved)
        alias = self.work / "linked-parent"
        self.symlink(alias, real, directory=True)
        self.process("--before", alias / "run", "--after", moved, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_run_and_control_parents_are_refused(self):
        run = self.run_fixture()
        alias = self.work / "run-junction"
        self.junction(alias, run["folder"])
        self.process("--before", alias, "--after", run["folder"], expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
        target = self.work / "owned-parent"
        target.mkdir()
        run2 = self.run_fixture()
        moved = target / "run"
        run2["folder"].rename(moved)
        parent_alias = self.work / "parent-junction"
        self.junction(parent_alias, target)
        self.process("--before", parent_alias / "run", "--after", moved, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_alternate_stream_controls_and_ambiguous_names_are_refused(self):
        run = self.run_fixture([record()])
        stream = str(run["folder"] / "files.csv") + ":fictional-stream"
        with open(stream, "wb") as handle:
            handle.write(b"Fictional named stream")
        self.compare(run)
        self.process("--before", str(run["folder"]) + ":fictional-stream", "--after", run["folder"],
                     expected=2, code="INPUT_PATH_INVALID")
        with open(stream, "rb") as handle:
            self.assertEqual(handle.read(), b"Fictional named stream")

    @unittest.skipUnless(os.name == "nt", "Native Windows held writer fixture")
    def test_native_windows_exclusive_writer_causes_concrete_open_refusal_then_release(self):
        run = self.run_fixture([record()])
        # Acquire in the child after the parent's preservation snapshot. Fixture
        # setup is outside main's exception handler and fails as an assertion.
        script = self.wrapper("""
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            held = kernel.CreateFileW(CONTROL_VALUE, 0x40000000, 0, None, 3, 0x80, None)
            if held == ctypes.c_void_p(-1).value:
                raise AssertionError('Native held writer fixture creation failed') from ctypes.WinError(ctypes.get_last_error())
            events.append(True)
            """.replace("CONTROL_VALUE", repr(str(run["folder"] / "files.csv"))),
                              postlude="assert kernel.CloseHandle(held)\nassert events == [True] and status == 2\n")
        self.run_cli(run, script=script, expected=2, code="INPUT_OR_REPORT_FAILED")
        self.compare(run)

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_controls_are_refused_before_open(self):
        for name in ("files.csv", "summary.json"):
            run = self.run_fixture()
            leaf = run["folder"] / name
            leaf.unlink()
            os.mkfifo(leaf, 0o600)
            self.run_cli(run, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_only_four_fixed_controls_are_read_without_source_execution_or_enumeration(self):
        run = self.run_fixture([record("inventoried/never-execute.py")])
        extra = run["folder"] / "tree.txt"
        extra.write_bytes(b"FICTIONAL_PRIVATE_UNDECLARED_CONTENT")
        script = self.wrapper("""
            allowed = {Path(RUN_VALUE) / name for name in ('files.csv', 'summary.json')}
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) in allowed, 'Inventoried source or undeclared file opened'
                events.append(Path(path).name)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Enumeration, source execution or network attempted')
            os.open = opened
            os.scandir = forbidden
            Path.iterdir = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            """.replace("RUN_VALUE", repr(str(run["folder"]))),
                              prelude="import socket, urllib.request, subprocess, runpy\n",
                              postlude="assert events == ['files.csv', 'summary.json', 'files.csv', 'summary.json'] and status == 0\n")
        self.assertEqual(self.run_cli(run, script=script), self.golden(run, run, [("inventoried/never-execute.py", "UNCHANGED")]))

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
        held = kernel.CreateFileW(str(link), 0x40000000, 0, None, 3, 0x02200000, None)
        if held == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            buffer = ctypes.create_string_buffer(data)
            returned = wintypes.DWORD()
            if not kernel.DeviceIoControl(held, 0x000900A4, buffer, len(data), None, 0,
                                          ctypes.byref(returned), None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(held)
        self.assertTrue(link.is_junction())


if __name__ == "__main__":
    unittest.main()
