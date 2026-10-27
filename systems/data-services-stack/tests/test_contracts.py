from base import Fixture, canonical, fictional_configuration
from copy import deepcopy
import json

from data_services.contracts import StackError, configuration, decode, fictional_input
from data_services.state import empty, validate


class Contracts(Fixture):
    def config(self, **changes):
        value = json.loads(fictional_configuration())
        value["jobs"][0].update(changes)
        return canonical(value)

    def test_fictional_configuration_is_strict_and_defensively_copied(self):
        result = configuration(fictional_configuration())
        self.assertEqual(result["sample"]["route"], "sample_route")
        result["sample"]["horizon"] = 99
        self.assertEqual(configuration(fictional_configuration())["sample"]["horizon"], 3)

    def test_unknown_fields_including_credentials_or_paths_are_refused(self):
        for name in ("password", "source_path", "provider", "extra"):
            with self.assertRaisesRegex(StackError, "JOB_SCHEMA_INVALID"):
                configuration(self.config(**{name:"fictional"}))

    def test_boolean_versions_and_unknown_top_level_fields_are_refused(self):
        for value in ({"version":True,"jobs":[]}, {"version":1,"jobs":[],"extra":1}, []):
            with self.assertRaises(StackError):
                configuration(canonical(value))

    def test_duplicate_json_keys_and_nonstandard_constants_are_refused(self):
        for raw in (b'{"version":1,"version":1}', b'{"value":NaN}', b'{"value":Infinity}'):
            with self.assertRaises(StackError):
                decode(raw)

    def test_malformed_and_oversized_json_have_fixed_codes(self):
        for raw in (b'{FICTIONAL_DO_NOT_ECHO', b'\xff', b'['*4000):
            with self.assertRaises(StackError) as error:
                decode(raw)
            self.assertNotIn("FICTIONAL_DO_NOT_ECHO", str(error.exception))
        with self.assertRaisesRegex(StackError, "JSON_BYTE_LIMIT"):
            configuration(b' '*65537)

    def test_job_count_and_duplicate_identifiers_are_bounded(self):
        template = json.loads(fictional_configuration())["jobs"][0]
        for jobs in ([], [template]*2, [dict(template,id="job"+str(i)) for i in range(17)]):
            with self.assertRaises(StackError):
                configuration(canonical(dict(version=1,jobs=jobs)))

    def test_job_numeric_parameters_refuse_booleans_and_invalid_ranges(self):
        for name,value in (("horizon",33),("window",0),("season",257),("max_attempts",6),("min_history",True)):
            with self.subTest(name=name), self.assertRaises(StackError):
                configuration(self.config(**{name:value}))

    def test_formats_methods_and_tokens_are_explicit(self):
        for changes in (dict(input_format="url"),dict(method="model"),dict(id="bad/name"),dict(route="bad route")):
            with self.assertRaises(StackError):
                configuration(self.config(**changes))

    def test_method_minimum_history_cannot_be_silently_adjusted(self):
        with self.assertRaisesRegex(StackError, "JOB_HISTORY_INVALID"):
            configuration(self.config(method="seasonal",season=4,min_history=3))

    def test_empty_state_is_canonical_and_unknown_schema_is_refused(self):
        self.assertEqual(validate(empty()), empty())
        with self.assertRaisesRegex(StackError, "STATE_SCHEMA_INVALID"):
            validate(dict(empty(),extra="fictional"))

    def test_state_rejects_noninteger_ticks_and_collection_capacity(self):
        for value in (True, -1, 1000000000001):
            with self.assertRaises(StackError):
                validate(dict(empty(),last_tick=value))
        with self.assertRaisesRegex(StackError, "STATE_CAPACITY_INVALID"):
            validate(dict(empty(),runs={str(i):{} for i in range(129)}))

    def test_run_fingerprint_and_queue_relationship_are_validated(self):
        self.create(run=True)
        from data_services.service import Stack
        with Stack(self.root) as app:
            state = deepcopy(app._state)
        bad = deepcopy(state)
        bad["runs"]["notice"]["fingerprint"] = "0"*64
        with self.assertRaisesRegex(StackError, "STATE_RUN_FINGERPRINT_INVALID"):
            validate(bad)
        bad = deepcopy(state)
        bad["queue"] = {}
        with self.assertRaisesRegex(StackError, "STATE_QUEUE_RELATION_INVALID"):
            validate(bad)

    def test_result_and_queue_code_types_are_validated_without_execution(self):
        self.create(run=True)
        from data_services.service import Stack
        with Stack(self.root) as app:
            state = deepcopy(app._state)
        for mutation in (lambda x:x["runs"]["notice"]["result"]["score"].update(mae=float("inf")),
                         lambda x:x["queue"]["notice"].update(code=[]),
                         lambda x:x["queue"]["notice"]["message"].update(body="Different fictional body.")):
            bad = deepcopy(state)
            mutation(bad)
            with self.assertRaises(StackError):
                validate(bad)
