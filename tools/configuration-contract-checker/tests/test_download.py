"""Actual copied-script consumers of fictional flat settings, never application configuration."""

import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FLAGS = dict.fromkeys(("network_probed", "programs_executed", "configuration_modified", "runtime_verified"), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def field(identifier="lower", *, key="FictionalLower", kind="integer", required=True, **constraints):
    return dict(id=identifier, key=key, type=kind, required=required, **constraints)


def rule(identifier="order", left="lower", right="upper"):
    return dict(id=identifier, op="less_or_equal", left=left, right=right)


def contract(fields=None, rules=None):
    return dict(schema_version=1, fields=default_fields() if fields is None else fields,
                rules=[rule()] if rules is None else rules)


def default_fields():
    return [field(minimum=0, maximum=10), field("upper", key="FictionalUpper", minimum=0, maximum=10),
            field("mode", key="FictionalMode", kind="string", required=False, choices=["fictional", "example"])]


def settings():
    return dict(FictionalLower=3, FictionalUpper=7, FictionalMode="fictional")


def valid_role(role):
    return contract() if role == "contract" else settings()


def checked(identifier, status="PASS", evidence="PRESENT_VALID", kind="field"):
    return dict(id=identifier, kind=kind, status=status, evidence=evidence)


def golden(rows, unexpected=0):
    counts = {key: sum(row["status"] == status for row in rows)
              for key, status in (("passed", "PASS"), ("failed", "FAIL"), ("not_supplied", "NOT_SUPPLIED"), ("blocked", "BLOCKED"))}
    counts["unexpected_settings"] = unexpected
    return dict(schema_version=1, status="REVIEW_REQUIRED" if counts["failed"] or counts["blocked"] or unexpected else "NO_DECLARED_VIOLATIONS",
                scope="DECLARED_FLAT_SETTINGS_ONLY", **FLAGS, counts=counts, checks=rows,
                issues=["SETTINGS_KEYS_UNDECLARED"] if unexpected else [])


def default_result():
    return golden([checked("lower"), checked("upper"), checked("mode"), checked("order", kind="rule", evidence="INTEGER_ORDER_SATISFIED")])


class Download(unittest.TestCase):
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or os.environ.get("OUTLANDS_TEST_TEMP")
                      or os.environ.get("TEMP") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="config-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.runtime = self.work / "copied single script"
        self.runtime.mkdir()
        self.source = self.runtime / "config_check.py"
        self.source.write_bytes((ROOT / "config_check.py").read_bytes())
        self.runtime_hash = sha(self.source.read_bytes())
        self.environment = os.environ.copy()
        self.environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "PYTHONSTARTUP"):
            self.environment.pop(name, None)
        self.serial = 0

    def fixture(self, value, *, raw=None):
        self.serial += 1
        path = self.work / ("FICTIONAL_PRIVATE_PLAN_" + str(self.serial) + ".json")
        path.write_bytes(json.dumps(value).encode("utf-8") if raw is None else raw)
        return path

    def wrapper(self, body, postlude="", prelude=""):
        self.serial += 1
        script = self.work / ("controlled-child-" + str(self.serial) + ".py")
        script.write_text("import sys, os\nfrom pathlib import Path\nimport importlib.metadata\n"
                          "assert sys.prefix != sys.base_prefix and not list(importlib.metadata.distributions())\n"
                          "sys.path.insert(0, " + repr(str(self.runtime)) + ")\n" + textwrap.dedent(prelude)
                          + "import config_check as tool\nevents = []\n" + textwrap.dedent(body)
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
                              capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60)
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
            self.assertEqual(set(value), {"schema_version", "status", "scope", "counts", "checks", "issues", *FLAGS})
            self.assertTrue(all(value[key] is False for key in FLAGS))
            for row in value["checks"]:
                self.assertEqual(set(row), {"id", "kind", "status", "evidence"})
        return value

    def run_cli(self, source=None, values=None, **options):
        return self.process("--contract", source or self.fixture(contract()), "--settings", values or self.fixture(settings()), **options)

    def run_role(self, role, selected, **options):
        return self.run_cli(source=selected, **options) if role == "contract" else self.run_cli(values=selected, **options)

    def check(self, schema, values, wanted, **options):
        self.assertEqual(self.run_cli(self.fixture(schema), self.fixture(values), expected=int(wanted["status"] == "REVIEW_REQUIRED"), **options), wanted)

    def symlink(self, path, target):
        self.assertTrue(path.is_relative_to(self.work) and target.is_relative_to(self.work))
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError as error:
            if (os.name == "nt" and getattr(error, "winerror", None) == 1314
                    and os.environ.get("OUTLANDS_CONFIG_REQUIRE_LINKS") != "1"):
                self.skipTest("Native symlink privilege unavailable")
            raise
        self.addCleanup(path.unlink)

    def test_complete_valid_dual_input_json_and_no_result_files(self):
        self.check(contract(), settings(), default_result())
        self.assertEqual({path.name for path in self.work.iterdir()}, {self.runtime.name, "FICTIONAL_PRIVATE_PLAN_1.json", "FICTIONAL_PRIVATE_PLAN_2.json"})

    def test_required_missing_and_optional_not_supplied_are_distinct(self):
        schema = contract([field(), field("optional", key="FictionalOptional", required=False)], [])
        self.check(schema, {"FictionalLower": 3}, golden([checked("lower"), checked("optional", "NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED")]))
        self.check(schema, {}, golden([checked("lower", "FAIL", "REQUIRED_SETTING_MISSING"), checked("optional", "NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED")]))

    def test_missing_operand_blocks_before_invalid_present_operand(self):
        schema = contract(default_fields()[:2], [rule()])
        for values, rows in [
            ({"FictionalLower": "fictional"}, [checked("lower", "FAIL", "TYPE_MISMATCH"), checked("upper", "FAIL", "REQUIRED_SETTING_MISSING")]),
            ({"FictionalUpper": 11}, [checked("lower", "FAIL", "REQUIRED_SETTING_MISSING"), checked("upper", "FAIL", "ABOVE_MAXIMUM")]),
        ]:
            self.check(schema, values, golden(rows+[checked("order", "BLOCKED", "DEPENDENCY_NOT_SUPPLIED", "rule")]))
        self.check(schema, {"FictionalLower": "fictional", "FictionalUpper": 7}, golden([
            checked("lower", "FAIL", "TYPE_MISMATCH"), checked("upper"), checked("order", "BLOCKED", "DEPENDENCY_INVALID", "rule")]))

    def test_only_individually_valid_operands_reach_literal_integer_order(self):
        schema = contract(default_fields()[:2], [rule()])
        for lower, upper, state, evidence in [(3, 7, "PASS", "INTEGER_ORDER_SATISFIED"), (7, 7, "PASS", "INTEGER_ORDER_SATISFIED"), (7, 3, "FAIL", "INTEGER_ORDER_VIOLATED")]:
            self.check(schema, dict(FictionalLower=lower, FictionalUpper=upper), golden([checked("lower"), checked("upper"), checked("order", state, evidence, "rule")]))
        self.check(schema, dict(FictionalLower=-1, FictionalUpper=7), golden([checked("lower", "FAIL", "BELOW_MINIMUM"), checked("upper"), checked("order", "BLOCKED", "DEPENDENCY_INVALID", "rule")]))

    def test_boolean_integer_and_signed_bounds_have_no_coercion(self):
        schema = contract([field("flag", key="FictionalFlag", kind="boolean"), field(minimum=0, maximum=10)], [])
        for value in (0, 10):
            self.check(schema, dict(FictionalFlag=True, FictionalLower=value), golden([checked("flag"), checked("lower")]))
        self.check(schema, dict(FictionalFlag=1, FictionalLower=True), golden([checked("flag", "FAIL", "TYPE_MISMATCH"), checked("lower", "FAIL", "TYPE_MISMATCH")]))
        self.check(schema, dict(FictionalFlag=False, FictionalLower=11), golden([checked("flag"), checked("lower", "FAIL", "ABOVE_MAXIMUM")]))
        for value in (-(2**63), 2**63-1):
            self.check(contract([field()], []), {"FictionalLower": value}, golden([checked("lower")]))
        for value in (-(2**63)-1, 2**63):
            self.run_cli(self.fixture(contract([field()], [])), self.fixture({"FictionalLower": value}), expected=2, code="SETTINGS_VALUE_UNSUPPORTED")

    def test_string_lengths_choices_and_keys_use_exact_codepoints(self):
        schema = contract([field("word", key="FictionalWord", kind="string", min_length=2, max_length=2)], [])
        self.check(schema, {"FictionalWord": "e\u0301"}, golden([checked("word")]))
        self.check(schema, {"FictionalWord": "é"}, golden([checked("word", "FAIL", "STRING_TOO_SHORT")]))
        self.check(schema, {"FictionalWord": "abc"}, golden([checked("word", "FAIL", "STRING_TOO_LONG")]))
        schema = contract([field("word", key="FictionalWord", kind="string", choices=["fictional", "e\u0301"])], [])
        for value in ("Fictional", "fictional ", "é", "$FICTIONAL", "~/fictional"):
            self.check(schema, {"FictionalWord": value}, golden([checked("word", "FAIL", "CHOICE_NOT_ALLOWED")]))
        self.check(schema, {"FictionalWord": "e\u0301"}, golden([checked("word")]))
        self.check(schema, {"fictionalword": "fictional"}, golden([checked("word", "FAIL", "REQUIRED_SETTING_MISSING")], 1))

    def test_checks_keep_field_then_rule_order_and_unexpected_keys_are_only_counted(self):
        schema = contract([field("upper", key="FictionalUpper"), field()], [rule("forward"), rule("reverse", "upper", "lower")])
        self.check(schema, dict(FictionalLower=3, FictionalUpper=7, FictionalPrivateExtra="FICTIONAL_PRIVATE_VALUE"), golden([
            checked("upper"), checked("lower"), checked("forward", kind="rule", evidence="INTEGER_ORDER_SATISFIED"), checked("reverse", "FAIL", "INTEGER_ORDER_VIOLATED", "rule")], 1))

    def test_seeded_independent_field_and_pairwise_rule_oracle_and_permutations(self):
        selected = random.Random(7021)
        for iteration in range(8):
            names = ["field_"+str(index) for index in range(5)]
            rows = [field(name, key="Key"+str(index), required=bool(index%2), minimum=0, maximum=8) for index, name in enumerate(names)]
            relations = [rule("edge_"+str(index), names[index], names[index+1]) for index in range(4)]
            values, wanted, states = {}, {}, {}
            for row in rows:
                candidate = selected.choice([None, True, -1, 0, 4, 8, 9])
                if candidate is not None:
                    values[row["key"]] = candidate
                if candidate is None:
                    state, evidence = ("FAIL", "REQUIRED_SETTING_MISSING") if row["required"] else ("NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED")
                elif type(candidate) is not int:
                    state, evidence = "FAIL", "TYPE_MISMATCH"
                elif candidate < 0:
                    state, evidence = "FAIL", "BELOW_MINIMUM"
                elif candidate > 8:
                    state, evidence = "FAIL", "ABOVE_MAXIMUM"
                else:
                    state, evidence = "PASS", "PRESENT_VALID"
                states[row["id"]] = state
                wanted[row["id"]] = checked(row["id"], state, evidence)
            keys = {row["id"]: row["key"] for row in rows}
            for relation in relations:
                left, right = relation["left"], relation["right"]
                if keys[left] not in values or keys[right] not in values:
                    state, evidence = "BLOCKED", "DEPENDENCY_NOT_SUPPLIED"
                elif states[left] != "PASS" or states[right] != "PASS":
                    state, evidence = "BLOCKED", "DEPENDENCY_INVALID"
                elif values[keys[left]] <= values[keys[right]]:
                    state, evidence = "PASS", "INTEGER_ORDER_SATISFIED"
                else:
                    state, evidence = "FAIL", "INTEGER_ORDER_VIOLATED"
                wanted[relation["id"]] = checked(relation["id"], state, evidence, "rule")
            for reverse in (False, True):
                fields_order = rows[::-1] if reverse else rows
                rule_order = relations[::-1] if reverse else relations
                self.check(contract(fields_order, rule_order), values, golden([wanted[row["id"]] for row in fields_order+rule_order]))

    def test_contract_and_field_schema_keys_ids_and_bounds_are_strict(self):
        for data in (None, [], {}, dict(contract(), schema_version=True), dict(contract(), private="FICTIONAL_PRIVATE_VALUE")):
            self.run_cli(self.fixture(data), expected=2, code="CONTRACT_SCHEMA_INVALID")
        samples = [({}, "FIELD_SCHEMA_INVALID"), (dict(field(), default=3), "FIELD_SCHEMA_INVALID"),
                   (field("Upper"), "CONTRACT_ID_INVALID"), (field(key="invalid key"), "FIELD_KEY_INVALID"),
                   (field(required=1), "REQUIRED_FLAG_INVALID"), (field(kind="Integer"), "FIELD_TYPE_INVALID"),
                   (field(minimum=True), "INTEGER_BOUND_INVALID"), (field(minimum=11, maximum=10), "INTEGER_BOUNDS_CONTRADICT"),
                   (field(kind="string", min_length=True), "STRING_BOUND_INVALID"),
                   (field(kind="string", min_length=3, max_length=2), "STRING_BOUNDS_CONTRADICT"),
                   (field(kind="string", choices=["same", "same"]), "STRING_CHOICES_INVALID"),
                   (field(kind="string", choices=["x"*129]), "STRING_CHOICES_INVALID"),
                   (field(kind="string", min_length=3, choices=["no"]), "STRING_CHOICES_INVALID")]
        for row, code in samples:
            self.run_cli(self.fixture(contract([row], [])), expected=2, code=code)
        self.run_cli(self.fixture(contract([field(), field("second")], [])), expected=2, code="DUPLICATE_FIELD_KEY")
        self.run_cli(self.fixture(contract([field(), field(key="Other")], [])), expected=2, code="DUPLICATE_CONTRACT_ID")

    def test_rules_require_distinct_declared_integer_ids_and_unique_ordered_pairs(self):
        for row, code in [({}, "RULE_SCHEMA_INVALID"), (dict(rule(), op="execute"), "RULE_OPERATION_INVALID"),
                          (rule(left="FictionalLower"), "RULE_REFERENCE_INVALID"), (rule(left="lower", right="lower"), "RULE_REFERENCE_INVALID"),
                          (rule("lower"), "DUPLICATE_CONTRACT_ID")]:
            self.run_cli(self.fixture(contract(rules=[row])), expected=2, code=code)
        self.run_cli(self.fixture(contract(rules=[rule(), rule("second")])), expected=2, code="DUPLICATE_RULE_PAIR")
        schema = contract([field(kind="boolean"), field("upper", key="FictionalUpper")], [rule()])
        self.run_cli(self.fixture(schema), expected=2, code="RULE_REFERENCE_INVALID")

    def test_flat_settings_types_and_4096_codepoint_limit_are_strict(self):
        for value in (None, [], "fictional", {"invalid key": 1}):
            self.run_cli(values=self.fixture(value), expected=2, code="SETTINGS_KEY_INVALID" if isinstance(value, dict) else "SETTINGS_SCHEMA_INVALID")
        for value in (None, [], {}, 1.0, "x"*4097):
            self.run_cli(values=self.fixture({"FictionalLower": value}), expected=2, code="SETTINGS_VALUE_UNSUPPORTED")
        self.check(contract([field("word", key="FictionalWord", kind="string")], []), {"FictionalWord": "x"*4096}, golden([checked("word")]))
        self.run_cli(values=self.fixture({"Key"+str(index): index for index in range(129)}), expected=2, code="SETTINGS_SCHEMA_INVALID")

    def test_64_kib_exact_bom_and_extra_byte_are_checked_for_each_input(self):
        for role in ("contract", "settings"):
            raw = b"\xef\xbb\xbf"+json.dumps(valid_role(role)).encode()
            exact = raw+b" "*(65536-len(raw))
            self.assertEqual(self.run_role(role, self.fixture(None, raw=exact)), default_result())
            self.run_role(role, self.fixture(None, raw=exact+b" "), expected=2, code="INPUT_SIZE_LIMIT")

    def test_duplicate_json_constants_encoding_and_malformed_data_in_each_input(self):
        for role in ("contract", "settings"):
            for raw, code in [(b'{"private":1,"private":2}', "DUPLICATE_JSON_KEY"), (b'{"private":NaN}', "NONSTANDARD_JSON"),
                              (b'{"private":Infinity}', "NONSTANDARD_JSON"), (b'{"private":-Infinity}', "NONSTANDARD_JSON"),
                              (b"\xff", "INPUT_OR_CONTRACT_FAILED"), (b"{", "INPUT_OR_CONTRACT_FAILED"), (b"{} trailing", "INPUT_OR_CONTRACT_FAILED")]:
                self.run_role(role, self.fixture(None, raw=raw), expected=2, code=code)

    def test_false_flags_and_full_reports_omit_setting_names_values_bounds_choices(self):
        schema = contract([field("public_id", key="FictionalPrivateKey", kind="string", choices=["FICTIONAL_PRIVATE_CHOICE"])], [])
        self.check(schema, {"FictionalPrivateKey": "FICTIONAL_PRIVATE_VALUE"}, golden([checked("public_id", "FAIL", "CHOICE_NOT_ALLOWED")]))
        self.check(schema, {"FictionalPrivateKey": "FICTIONAL_PRIVATE_CHOICE"}, golden([checked("public_id")]))

    def test_help_version_arguments_and_path_errors_are_static_private_json(self):
        for argument in ("--help", "--version"):
            output = self.process(argument, json_output=False)
            self.assertIn("configuration-contract-checker", output)
        for args in ((), ("--contract", "FICTIONAL_PRIVATE_MISSING"), ("--settings", "FICTIONAL_PRIVATE_MISSING"),
                     ("--contr", "x", "--settings", "y"), ("--contract", "x", "--sett", "y"), ("--report", "FICTIONAL_PRIVATE_OUTPUT")):
            self.process(*args, expected=2, code="ARGUMENTS_INVALID")
        for role in ("contract", "settings"):
            self.run_role(role, self.work/"FICTIONAL_PRIVATE_MISSING.json", expected=2, code="INPUT_OR_CONTRACT_FAILED")
            self.run_role(role, self.runtime, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
            for path in (self.work/"CON.json", self.work/"file:stream", self.work/".."/"escape.json"):
                self.run_role(role, path, expected=2, code="INPUT_PATH_INVALID")

    def test_only_two_selected_inputs_are_read_without_network_process_or_environment_changes(self):
        source, values = self.fixture(contract()), self.fixture(settings())
        (self.work/"unrelated-configuration.txt").write_bytes(b"FICTIONAL_PRIVATE_CONFIG_NEVER_OPEN")
        (self.work/"prior-capture.txt").write_bytes(b"Fictional prior capture must remain unchanged\n")
        script = self.wrapper("""
            selected = [Path(CONTRACT), Path(SETTINGS)]
            environment_before = dict(os.environ)
            original = os.open
            def opened(path, *args, **kwargs):
                assert Path(path) == selected[len(events)], 'Unselected input opened'
                events.append(True)
                return original(path, *args, **kwargs)
            def forbidden(*args, **kwargs):
                raise AssertionError('Network, process, environment change or enumeration attempted')
            os.open = opened
            os.scandir = forbidden
            os.listdir = forbidden
            os.putenv = forbidden
            os.unsetenv = forbidden
            Path.open = forbidden
            socket.socket = forbidden
            socket.create_connection = forbidden
            socket.getaddrinfo = forbidden
            socket.gethostbyname = forbidden
            urllib.request.urlopen = forbidden
            subprocess.Popen = forbidden
            runpy.run_path = forbidden
            os.system = forbidden
            os.execv = forbidden
            """.replace("CONTRACT", repr(str(source))).replace("SETTINGS", repr(str(values))), prelude="import socket, urllib.request, subprocess, runpy\n",
                              postlude="assert events == [True, True] and status == 0\nassert dict(os.environ) == environment_before\n")
        self.assertEqual(self.run_cli(source, values, script=script), default_result())

    def test_128_field_rule_setting_boundaries_and_32_choices_are_enforced(self):
        rows = [field("f"+str(index), key="Key"+str(index)) for index in range(128)]
        relations = [rule("r"+str(index), rows[index%128]["id"], rows[(index+1)%128]["id"]) for index in range(128)]
        self.check(contract(rows, relations), {row["key"]: 3 for row in rows}, golden(
            [checked(row["id"]) for row in rows]+[checked(row["id"], kind="rule", evidence="INTEGER_ORDER_SATISFIED") for row in relations]))
        for schema in (contract([], []), contract(rows+[field("extra", key="Extra")], []), contract(rows, relations+[rule("extra", "f0", "f2")])):
            self.run_cli(self.fixture(schema), expected=2, code="CONTRACT_SCHEMA_INVALID")
        choices = ["value"+str(index) for index in range(32)]
        self.check(contract([field("word", key="FictionalWord", kind="string", choices=choices)], []), {"FictionalWord": choices[-1]}, golden([checked("word")]))
        self.run_cli(self.fixture(contract([field("word", key="FictionalWord", kind="string", choices=choices+["extra"])], [])), expected=2, code="STRING_CHOICES_INVALID")

    def test_native_hardlinked_input_is_refused_and_target_preserved(self):
        for role in ("contract", "settings"):
            source = self.fixture(valid_role(role))
            alias = self.work/(role+"-hardlink.json")
            os.link(source, alias)
            self.assertGreaterEqual(source.stat().st_nlink, 2)
            self.run_role(role, source, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    def test_controlled_interrupt_and_short_read_release_each_input_handle(self):
        for role in ("contract", "settings"):
            for mode in ("interrupt", "short"):
                source = self.fixture(valid_role(role))
                script = self.wrapper("""
                    original_open, original_fdopen = os.open, os.fdopen
                    targeted, descriptors = set(), []
                    def opened(path, *args, **kwargs):
                        fd = original_open(path, *args, **kwargs)
                        descriptors.append(fd)
                        if Path(path) == Path(INPUT_VALUE):
                            targeted.add(fd)
                        return fd
                    class Controlled:
                        def __init__(self, stream): self.stream = stream
                        def __enter__(self):
                            self.stream.__enter__()
                            return self
                        def __exit__(self, *args): return self.stream.__exit__(*args)
                        def fileno(self): return self.stream.fileno()
                        def read(self, maximum):
                            events.append(True)
                            if MODE == 'interrupt':
                                raise KeyboardInterrupt('FICTIONAL_PRIVATE_INTERRUPT')
                            return self.stream.read(maximum)[:-1]
                    def wrapped(fd, *args, **kwargs):
                        stream = original_fdopen(fd, *args, **kwargs)
                        return Controlled(stream) if fd in targeted else stream
                    os.open, os.fdopen = opened, wrapped
                    """.replace("INPUT_VALUE", repr(str(source))).replace("MODE", repr(mode)), postlude="""
                    assert events == [True]
                    for fd in descriptors:
                        try: os.fstat(fd)
                        except OSError as error: assert error.errno == 9
                        else: raise AssertionError('Owned input descriptor remained open')
                    """)
                self.run_role(role, source, script=script, expected=130 if mode == "interrupt" else 2, code="INTERRUPTED" if mode == "interrupt" else "INPUT_CHANGED")

    def test_observed_identity_change_and_native_read_error_in_each_input_are_fixed(self):
        for role in ("contract", "settings"):
            source = self.fixture(valid_role(role))
            script = self.wrapper("""
                original = tool._snapshot
                def changed(path):
                    ancestors, leaf = original(path)
                    if path == Path(INPUT_VALUE):
                        events.append(True)
                        if len(events) == 2:
                            ancestors += ('controlled observed change',)
                    return ancestors, leaf
                tool._snapshot = changed
                """.replace("INPUT_VALUE", repr(str(source))), postlude="assert events == [True, True] and status == 2\n")
            self.run_role(role, source, script=script, expected=2, code="INPUT_CHANGED")
            script = self.wrapper("""
                original = os.open
                def denied(path, *args, **kwargs):
                    if Path(path) == Path(INPUT_VALUE):
                        events.append(True)
                        raise OSError('FICTIONAL_PRIVATE_NATIVE_IO_DETAIL')
                    return original(path, *args, **kwargs)
                os.open = denied
                """.replace("INPUT_VALUE", repr(str(source))), postlude="assert events == [True] and status == 2\n")
            self.run_role(role, source, script=script, expected=2, code="INPUT_OR_CONTRACT_FAILED")

    def test_native_symlink_input_leaf_and_dangling_are_refused(self):
        for role in ("contract", "settings"):
            source = self.fixture(valid_role(role))
            alias = self.work/(role+"-linked.json")
            self.symlink(alias, source)
            self.run_role(role, alias, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
            absent = self.work/(role+"-absent.json")
            dangling = self.work/(role+"-dangling.json")
            self.symlink(dangling, absent)
            self.run_role(role, dangling, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")
            self.assertFalse(absent.exists())

    def test_native_symlink_input_parent_is_refused(self):
        for role in ("contract", "settings"):
            target = self.work/(role+"-owned-parent")
            target.mkdir()
            source = target/"input.json"
            source.write_bytes(json.dumps(valid_role(role)).encode())
            alias = self.work/(role+"-linked-parent")
            self.symlink(alias, target)
            self.run_role(role, alias/source.name, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows junction fixture")
    def test_native_windows_junction_input_parent_is_refused(self):
        for role in ("contract", "settings"):
            target = self.work/(role+"-owned-parent")
            target.mkdir()
            source = target/"input.json"
            source.write_bytes(json.dumps(valid_role(role)).encode())
            alias = self.work/(role+"-junction-parent")
            self.junction(alias, target)
            self.run_role(role, alias/source.name, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

    @unittest.skipUnless(os.name == "nt", "Native Windows alternate stream fixture")
    def test_native_windows_named_stream_is_not_part_of_selected_input(self):
        for role in ("contract", "settings"):
            source = self.fixture(valid_role(role))
            stream = str(source)+":fictional-stream"
            with open(stream, "wb") as handle: handle.write(b"FICTIONAL_PRIVATE_NAMED_STREAM")
            self.assertEqual(self.run_role(role, source), default_result())
            self.run_role(role, stream, expected=2, code="INPUT_PATH_INVALID")
            # Measured retained normalization, not a suffix-refusal guarantee.
            for spelling in (str(source)+".", str(source)+" ", str(source.parent)+"."+os.sep+source.name):
                self.assertEqual(self.run_role(role, spelling), default_result())
            self.run_role(role, str(source.parent)+" "+os.sep+source.name, expected=2, code="INPUT_PATH_INVALID")
            with open(stream, "rb") as handle: self.assertEqual(handle.read(), b"FICTIONAL_PRIVATE_NAMED_STREAM")

    @unittest.skipUnless(os.name == "nt", "Native Windows held writer fixture")
    def test_native_windows_exclusive_writer_causes_open_refusal_then_release(self):
        for role in ("contract", "settings"):
            source = self.fixture(valid_role(role))
            script = self.wrapper("""
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
                kernel.CreateFileW.restype = wintypes.HANDLE
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                kernel.CloseHandle.restype = wintypes.BOOL
                held = kernel.CreateFileW(INPUT_VALUE, 0x40000000, 0, None, 3, 0x80, None)
                if held == ctypes.c_void_p(-1).value:
                    raise AssertionError('Native held writer fixture creation failed') from ctypes.WinError(ctypes.get_last_error())
                events.append(True)
                """.replace("INPUT_VALUE", repr(str(source))), postlude="assert kernel.CloseHandle(held)\nassert events == [True] and status == 2\n")
            self.run_role(role, source, script=script, expected=2, code="INPUT_OR_CONTRACT_FAILED")
            self.assertEqual(self.run_role(role, source), default_result())

    @unittest.skipUnless(os.name != "nt", "Native POSIX FIFO fixture")
    def test_native_posix_fifo_input_is_refused_before_open(self):
        for role in ("contract", "settings"):
            fifo = self.work/(role+"-fifo.json")
            os.mkfifo(fifo, 0o600)
            self.run_role(role, fifo, expected=2, code="INPUT_UNAVAILABLE_OR_UNSAFE")

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
        substitute = ("\\??\\"+str(target)).encode("utf-16-le")
        printable = str(target).encode("utf-16-le")
        payload = substitute+b"\x00\x00"+printable+b"\x00\x00"
        data = struct.pack("<LHHHHHH", 0xA0000003, 8+len(payload), 0,
                           0, len(substitute), len(substitute)+2, len(printable))+payload
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
