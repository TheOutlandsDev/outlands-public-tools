# Install and use the document and answer-evidence tools

Review explicit document snapshots, chunk plans, supplied search rankings and
answer citation records. Start with the [plain-language definitions](../../methodology/DOCUMENT-EVIDENCE.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel includes a CLI, an embedded fictional demo and its documented Python API.
Supply Python 3.12 or 3.13; runtime code uses only the standard library.

| Tool | When to use it | Fictional input and expected output | What the result establishes |
| --- | --- | --- | --- |
| [Context Manifest Checker](../../tools/context-manifest-checker/README.md) | Review selected document revisions and declared dependencies. | Orchard depends on garden, with meadow independent: order garden, meadow, orchard. A dependency cycle withholds the complete manifest/order. | Exact supplied text pins, references and acyclic dependency declarations agree. |
| [Document Chunk Planner](../../tools/document-chunk-planner/README.md) | Plan reproducible character windows while retaining source identity. | ABCDEFGHIJK, width 5, overlap 2: [0,5), [3,8), [6,11), with substring hashes and omitted bodies. | The bounded selected text is covered under the explicit code-point policy. |
| [Retrieval Evaluation Calculator](../../tools/retrieval-evaluation-calculator/README.md) | Score supplied rankings against selected binary relevance judgments. | The embedded two-query example at k=2 gives macro precision 1/2, macro recall 3/4 and MRR 3/4. | Exact arithmetic under supplied rankings, judgments and k. |
| [Answer Evidence Checker](../../tools/answer-evidence-checker/README.md) | Check explicit source/span/quote records for a supplied answer. | Exact garden quote [0,17) passes; changed quote or stale revision withholds all evidence. | Structural citation integrity; claim support and factual truth remain unverified. |

These tools read one explicitly supplied JSON input. They do not search a corpus,
call a model, generate answers, create embeddings or approve publication. Pins
bind supplied decoded text; source-file bytes, authority, rights and privacy need
separate review. Source guides define complete schemas, row accounting and limits.

## Install one tool or the four-tool collection

Download the selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/document-evidence-wheels-v1.0.0).
Verify SHA-256. One tool needs only its own wheel; the collection needs all five
wheels in one directory outside source. Create a fresh environment using
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_context_manifest_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-document-evidence-collection==1.0.0
```

On PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`; on Ubuntu use
`./ENV/bin/python`. Commands live in that environment's Scripts or bin directory.
Run `outlands-context-manifest-checker-demo` for its embedded fictional fixture or
`outlands-context-manifest-checker --input PRIVATE_JSON` for selected input.
Use literal wheel/command names from components.json for the other tools.
`outlands-document-evidence` lists the four commands. These are downloadable wheels;
no package-index registration is implied. Actual documents and reports stay private.

## Call a tool from another project or AI workflow

This literal example uses an embedded fictional input and the chunk planner's
actual `plan` operation:

```python
from importlib.resources import files
from outlands_document_chunk_planner.chunks import plan
raw = files("outlands_document_chunk_planner").joinpath("examples", "input.json").read_bytes()
report = plan(raw)
assert report["status"] == "PASS"
assert report["offset_unit"] == "UNICODE_CODE_POINT"
assert report["text_emitted"] is False
```

The four API operations are `context_manifest.check`, `chunks.plan`,
`retrieval.calculate` and `evidence.check`, each under its `outlands_...` package
listed in components.json. AI callers can read that guide for exact imports,
formats, examples and result fields. Pass raw JSON bytes, preserve exact decoded
text/revisions/pins, and inspect status, issues, row counts and derived fields
together. REVIEW_REQUIRED exits 1 and withholds the complete derived result;
malformed outer API input raises a fixed refusal and the CLI exits 2. Do not infer
truth from citation PASS or change precision's denominator when fewer results arrive.

## Worked workflow and project connection

With the collection installed, run
`python -B integrations/document-evidence/exercise.py` from the repository root.
It binds one invented document across all four tools, plans three overlapping
windows, scores a supplied ranking, and uses the middle window as an exact
citation. The quote hash must equal that window's hash. It also demonstrates
an unrelated answer that passes structure while truth remains unverified,
wrong/stale citations, a dependency cycle, absent judgments versus zero results,
and Unicode code points versus UTF-8 bytes. No source/answer/quote body is emitted.

The [Corpus & Model Workbench](../../systems/corpus-model-workbench/README.md)
is a related application for reviewed corpus material, search, exports and local
model-response comparisons. A caller-owned adapter must select materialized text,
map corpus/context/message IDs to explicit document IDs and revisions, recompute
these decoded UTF-8 text pins, and declare dependencies rather than infer them.
Workbench materialized-message approval hashes, backup receipts and source-file
hashes are different domains and must not be substituted. Its materialized context
can exceed these tools' per-document limits; any reviewed partitioning must be
explicit rather than silent truncation. A caller must separately provide ranked
document references, relevance judgments and citation spans. Character chunking
does not establish model token budgets or implement the Workbench's embedding or
semantic-search behavior. No adapter or live integration is implemented or qualified.
Workspaces, prompts, model names/endpoints, histories, judgments and exports stay
private. Structural evidence PASS does not replace content approval or truth review.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/document-evidence/build_wheels.py --output DIRECTORY` and
`python -B integrations/document-evidence/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Fixed synthetic archive metadata retains public MIT attribution and required package
metadata. Hosted Windows/Ubuntu Python 3.12/3.13 checks fresh-install every tool and
the collection, run CLI/demo/API/review cases, execute the workflow and literal API
example, and compare exact bytes. Anonymous public-download checks repeat after
publication. Qualification covers fictional inputs and package behavior.
