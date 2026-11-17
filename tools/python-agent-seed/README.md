# Python Coding Agent Seed & Evaluation Kit

A runnable developer kit with original coding instructions, link-first source
metadata, good/bad examples and five small repair exercises. All 63 selected
original text/source files are preserved byte for byte in `original/`, including
eight example tests and 18 evaluation test definitions. Separate reference repairs
and a reviewed fixture runner surround that material; no starter or test is replaced.

Download the [source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/python-agent-seed-v0.1.0).
See [setup and exercise workflow](SETUP.md), [qualification](docs/QUALIFICATION.md)
and [origins](docs/ORIGINS.md). Python 3.12.16 and 3.15.2 are the pinned Windows x64/
Ubuntu x86-64 qualification targets. Runtime and tests use the standard library;
no pip package, model, account, cloud service or installed coding agent is required.

```text
python kit.py inspect
python run_checks.py --report NEW_EXTERNAL_REPORT.json
python kit.py prepare --task eval_001_pathlib_json_loader --out NEW_EXTERNAL_EXERCISE_DIRECTORY
```

The full check has three positive populations: eight original good-example tests,
18 unchanged original evaluation tests against separate reference repairs, and ten
release/CLI checks. All 36 must pass. The deliberately flawed original starters are
also observed separately: 18 test definitions produce eight actual method starts
and two load-failure framework entries, ten framework entries total. Their expected
baseline is one pass, three assertion failures and six errors (including two import
failures). Ten definitions cannot run until the missing result classes exist. These
outcomes are recorded explicitly; no unloadable test is counted as executed/passing.

`kit.py evaluate --mode starter --task TASK_ID` returns exit 0 when the expected
flawed baseline is observed. Its success=false and error/failure fields remain in
JSON. That exit is not a passing solution. Reference mode requires the original
tests to pass. The legacy template retains its original unittest exit behavior.
`kit.py check` runs the 26 example/reference methods plus starter observations and
legacy CLI smoke checks; `run_checks.py` additionally runs the ten release methods.

The runner launches only fixed reviewed task IDs in separate interpreter processes
with private working directories. Audit hooks refuse network/process events, except
the good example's exact harmless Python print command, and refuse execution of
the five excluded bad-example files. Three refused canaries verify these hooks.
The socket canary emits the audit event without making a connection. These hooks
are checks around known reviewed fixtures, not OS containment for untrusted code.
They do not restrict all file access. The bad-example files remain teaching data.

`prepare` copies one original exercise's five files into a NEW private directory
outside this package and writes a copy manifest. It executes nothing, refuses links/
reparse paths and existing outputs, and leaves the pinned package unchanged. A disk
failure can leave a partial new directory. Use stable trusted parents; this is not
protection against hostile concurrent filesystem replacement. Edit and test your
own prepared copy using an environment appropriate for the code you choose to run.

The original instructions target Python 3.12.7 and remain historical source data.
They are not automatically installed as agent policies. The 39 source links and
license/availability notes are also preserved historical metadata; independently
review each upstream before retrieval or reuse. The checker fetches none of them.
No third-party documents, books, courseware, corpora, histories, caches or runtimes
are bundled. The supplied reference answers are separate and visible; this small
practice kit does not measure unseen-model capability, security or production readiness.
Original examples and references are intentionally narrow teaching implementations.
