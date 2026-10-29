# Planner Input Handoff Checker

Check an explicitly reviewed, hash-pinned project against the existing public
planner's actual project contract and calculation checks. Target behavior is
**plan-only**. No project import, target update, database access, shipment action
or lot reservation occurs. Python 3.12/3.13, MIT TheOutlandsDev.

This tool includes pinned copies of already-public planner models/engines and a
new in-memory runtime shim. It selects no original private application, mapping,
formula, production workbook, configuration, credential or record. The fixture
project is the already-public invented two-product example.

Install the hash-pinned third-party dependencies in a dedicated environment:

```text
python -m pip install --require-hashes --only-binary=:all: -r requirements.txt
python -B handoff.py --project examples/project.json --handoff examples/handoff.json --attachment provenance examples/provenance.txt
```

Run from this tool directory. The example returns exit 0/PASS, with explicit
import eligibility and all execution/authority flags false. Requirements cover
CPython 3.12/3.13 Windows x64 and glibc Linux x86_64 wheels. No dependency is
installed by the checker. Missing model dependencies return a fixed diagnostic.

Library: `handoff.check(project_bytes, handoff_bytes, {'provenance': buffer})`.
No sibling workbench installation is required. No code from inputs is imported.

## Exact review boundary

[handoff.json](examples/handoff.json) uses `outlands-planner-handoff-v1`: the exact
raw project SHA-256, an explicit ID/hash attachment list and a review object.
The review separately pins the current project and the sorted attachment set,
and explicitly asserts `inputs_reviewed`, `mappings_reviewed`, `policies_reviewed`
and `plan_only`. Missing flags are not defaulted. False flags or stale pins
withhold `eligible_for_explicit_import`; boolean-like strings/integers are invalid.

`handoff.attachment_pin(buffers)` computes SHA-256 over the ASCII, sorted-key,
compact JSON array of `{id,sha256}` objects sorted by ID, with one final LF.
All declared attachments must be explicitly bound exactly once on the CLI using
`--attachment ID FILE`; no manifest path, URL or folder is followed. Empty
attachments are allowed only with the matching explicit empty-set review pin.
Attachments are opaque evidence buffers: their contents and sufficiency are not
semantically authenticated. A hash/checkbox is not a signature or verified human
identity, and an attacker replacing the review and project can create matching pins.

The selected project must pass the pinned public parser **and** calculation
checks, including strict quantities, product/policy alignment, mapped WIP,
versioned demand and handoff conservation. This wrapper additionally rejects
floating JSON literals; express Decimal policy values as strings. The public
project schema is reproduced in [project.json](examples/project.json), with
constraints in [the existing planner contract](../../systems/production-planning-workbench/docs/CONTRACT.md).
When copied alone, use the included fixture, source models and this guide; the
collection-relative link is supplemental. There is no inferred mapping from an
intake preview, XML workflow or snapshot into a planner project.

PASS is a point-in-time check of supplied buffers. To use the existing planner,
explicitly import the **same project bytes** through its documented workflow;
the checker report itself is not a planner project. Downstream import is separate
and does not enforce this review report automatically. A later changed project
needs new pins/review and another check. This tool does not write, migrate or
approve an existing planner store and does not claim production authority.

## Bounds and output

4 MiB per selected file; 16 attachments, 16 MiB total attachment buffers; JSON
depth 32/100,000 nodes, no duplicate keys or nonfinite numbers. The public
project's collection, timing, quantity and lot-proposal limits remain active.
Source inputs are read sequentially into retained buffers, not as an atomic
multi-file capture. Private stdout includes project identity, content hashes and
review outcomes; it contains no copied project/attachment payloads.

Optional `--out NEW_PRIVATE_REPORT.json` exclusively creates a fresh external
report. Inputs, reports and reviewed hashes may identify a private system and
remain private. See [I/O limits](IO-SAFETY.md), [origins and public pins](ORIGINS.md)
and [validation](VALIDATION.md). Exit 0 PASS; 1 incomplete/stale review; 2 invalid
project/arguments or refused I/O; 130 handled interruption.
