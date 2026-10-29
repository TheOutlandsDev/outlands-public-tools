# Fictional validation and limits

Run from this directory with Python 3.12/3.13 (install the pinned requirements first
for Planner Input Handoff Checker):

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

The repository qualification workflow runs all four tools on Windows/Ubuntu,
Python 3.12/3.13. Native hardlink and directory-junction/symlink fixtures are
required there using OUTLANDS_INTAKE_REQUIRE_LINKS=1; unavailable native fixtures
fail qualification. Only genuinely opposite-platform methods are skipped.
Local filesystems without native fixture support can explicitly report skips;
that local result does not substitute for the native matrix.

Tests cover invented input semantics, resource/schema refusals, fixed-code
argument diagnostics, native ordinary reads/exclusive writes, hardlink and linked
ancestor refusal, overwrite/source-output prevention and retained failed output.
See tests/ for the exact per-tool cases. The shared public backend bytes and
planner engine copies are compared against their collection counterparts.

From the collection root, the actual CLI/copy/handoff walkthrough is:

```text
python -B -W error -m unittest discover -s tests -p test_intake_parser_tools.py -v
```

It runs each tool copied into its own fresh directory, checks its source manifest,
creates new private reports, refuses overwrite, generates a fictional workbook,
compares CSV/XLSX normalized output and explicitly reviews a four-tool handoff.
Changed evidence must invalidate the prior review. No automatic mapping into the
planner, original record, original operational instance or external system is used.

This qualification does not exercise Excel/LibreOffice GUI round trips, real
workbooks, production source systems, network shares, hostile/privileged filesystem
races, power-loss durability, live database imports or business-policy correctness.
Generated XLSX tests qualify the documented subset only. Review flags and pins
are local declarations; they do not prove authenticated approval. Runtime outputs,
failed test evidence and private source audits are not publication artifacts.
