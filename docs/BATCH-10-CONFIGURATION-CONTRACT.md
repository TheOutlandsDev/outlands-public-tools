# Offline Configuration Contract Checker review — 2026-10-25

This batch adds [Offline Configuration Contract Checker](../tools/configuration-contract-checker/README.md)
and a neutral [Diagnostic Evidence Plan](../methodology/diagnostic-evidence-plan.md).
The new validator follows a fresh public specification, informed only by the
audit's generic configuration-validation candidate. No held original server or
hobby source, private schema, configuration or operational record was selected,
read, copied or executed for this addition. The earlier source-family holds are
not cleared by this implementation. Input metadata handling adapts the existing
MIT public Connection Plan Checker pattern.

## Behavior and public boundary

The Python 3.12+ standard-library CLI reads two explicit JSON files: a declared
contract and flat scalar settings. Contracts declare unique field IDs/keys,
boolean/integer/string types, required flags, integer bounds, string lengths
and choices, plus integer `less_or_equal` rules referencing field IDs. Settings
outside the declared key set require review without exposing their names.
Unsupported types, nesting, invalid contracts and unsafe inputs are refused.

There is no general JSON Schema interpreter, arbitrary expression, script,
regex constraint, reference resolver, environment expansion, coercion, default
application, network/service probe, target execution or configuration mutation.
Values that resemble paths or commands are data and are never followed or run.
The CLI writes only to stdout and has no report-file writer.

Optional absent values are `NOT_SUPPLIED`, not validated values. Rules with
missing or individually invalid operands are `BLOCKED`. Only two present,
valid integer operands can produce a rule pass or failure. A result with no
declared violations does not prove application compatibility, security,
runtime acceptance or that any optional value was checked.

Results contain declared IDs, fixed statuses/evidence, counts and fixed issue
codes. Setting keys, values, bounds, choices, paths and native exception text
are omitted. IDs and outcomes can still reveal private design. Real contracts,
settings, outputs and completed evidence plans stay private; this tool is not
an anonymizer, secret scanner or approval to publish operator input.

Each JSON input is limited to 64 KiB; fields, rules and settings keys have
separate 128-entry bounds. Integers are signed 64-bit, strings at most 4,096
Unicode code points, choices at most 32 strings of at most 128 code points.
String matching is exact and case-sensitive, with no Unicode normalization.
File/ancestor identities, regular-file/single-link checks and link/reparse
checks are sampled before/after a bounded read. Use stable trusted local files;
this is not an atomic two-file snapshot or hostile-filesystem sandbox. Mapped
or mounted storage can involve OS network I/O, and size bounds do not interrupt
blocked filesystem calls. Formatted reader errors suppress native input detail
but still include Python source locations when an API caller prints a traceback.

## Validation

Fictional tests cover contract and settings schemas, scalar and resource
bounds, contradictory constraints, copied input objects, rule references,
optional/missing/invalid dependencies, unknown-key redaction, string semantics,
input identity checks, malformed JSON, fixed error handling and absence of
network/process/target-read/output-file activity. The local Windows/Python
3.12.7 utility suite discovered 44 methods: 42 passed and two unavailable native
link operations were skipped. The collection regression discovered 267 methods:
254 passed and 13 were skipped, with no failures/errors. Skips are not passes.

Independent review passed 111 bounded adversarial probes. Twenty-four separate
fictional CLI scenarios passed, including the documented valid, invalid and
incomplete examples; example hashes remained unchanged. Ruff checks/formatting
and 156 local document checks passed. No real configuration was used.

The dedicated workflow runs the fictional suite on Windows and Ubuntu with
Python 3.12/3.13 and checks local documentation/JSON syntax. See the exact
commit's Actions results for executed platforms. No real configuration or
production application is accepted by these tests.

Selected original source, tests, documentation and fictional examples use MIT
with TheOutlandsDev attribution. No third-party implementation or runtime is
bundled. Private marker lists, source mappings, audit output, local evidence
and publication receipts remain outside this repository. Review is limited to
this addition and its changed documentation, not historical objects, unrelated
concurrent imports, release assets or the full private drive.

The exact 15-file publication set retains one conservative scanner finding: an
invented UNC path in a negative input test. The test requires refusal before
filesystem access; it contains no discovered host or operational path. The
finding has a private file-hash-bound disposition. Scanner status remains
`REVIEW_REQUIRED`, with no detector disabled and zero unresolved findings after
review. There were no private-marker matches or scanner errors.
