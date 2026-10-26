# Validation and evidence boundaries

From the module folder run `python -B source_check.py` and
`python -B -W error -m unittest discover -s tests -v`.

Local validation uses CPython 3.12.7 on Windows with disposable authored inputs.
CI runs all three source gates/suites on Ubuntu Python 3.12/3.13 and Windows
Python 3.13/3.14, with warnings treated as errors. Shared tests are intentionally
repeated across standalone modules; they are not unique product features.
Windows alternate-stream syntax is tested only on Windows; POSIX FIFOs only
where available. Link tests skip when the environment cannot create the link.
Skips are recorded separately from passes.

Specific fixtures exercise exact timestamp arithmetic, event identity/privacy,
supported XML/JSON and gaps; literal property parsing/duplicates/import coverage;
and permission numeric normalization, unsupported-path holds and optional fields.
Shared tests cover stable read-only input, fresh output, bounds, escaping and
report manifests. The actual CLI runs generated examples with expected exits.
No arbitrary program or selected input is executed by inspection.

Manual export instructions are separate operator actions. No real Windows event
query or raw private export was performed during this validation. Generated
time gaps are not device-failure or causation proof. Snapshot comparisons do not
establish effective Android configuration, access policy, actual file existence
or successful boot/deployment. Read the format and coverage lists.

Source manifests verify an explicit reviewed UTF-8 source-only allowlist. They
are unsigned and do not authenticate authorship or guarantee universal secret
absence. CI results for the source commit are available under repository Actions.
