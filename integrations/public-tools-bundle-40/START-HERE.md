# OUTLANDS forty-tool install bundle

This ZIP contains forty independent MIT Python tool wheels, ten group
installers and selector v1.8.0. Supply Python 3.12 or 3.13 and pip separately.
COMPONENTS.json describes purposes, use cases, APIs, formats and limits. No runtime,
real inputs, private records, profiles, logs or application adapters are included.

Download the ZIP and outer SHA256SUMS.txt from the same
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.8.0).
Verify the ZIP SHA-256 before extracting into a new folder outside the checkout.
Inner SHA256SUMS.txt pins all fifty-one wheels; MANIFEST.json pins every other
archive member. Create a fresh environment outside that extracted folder with
`py -3.12 -m venv ../ENV` on Windows or `python3.12 -m venv ../ENV` on Ubuntu.
From the extracted root, use that environment's Python:

```text
python -m pip install --no-index --no-deps wheels/outlands_relational_schema_diff-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[routing]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ai]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[probability]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[cache]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[review]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[test]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[reliability]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[metrics]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[documents]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[relational]==1.8.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[all]==1.8.0"
```

The first installs one tool; substitute any individual filename from COMPONENTS.json.
Other choices install one four-tool group or all forty. On PowerShell use
`& ../ENV/Scripts/python.exe` for Python; on Ubuntu use `../ENV/bin/python`.
Commands are in that environment's Scripts or bin directory. `outlands-public-tools`
lists commands and actual installed state. Each individual command has an embedded
fictional `-demo` command and accepts an explicit private JSON input.

## Select by task

| Group | Use it for | Definitions, examples and integration |
| --- | --- | --- |
| routing | Model capability, compatibility and route declarations | [Model routing](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/model-routing) |
| ai | Prompt contracts, label mapping, abstention and evaluation gates | [AI decision contracts](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/ai-decision-contracts) |
| probability | Probability, interval and ranking declaration checks | [Probability integrity](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/probability-integrity) |
| cache | Cache keys, freshness, retry budgets and idempotency claims | [Cache and retry](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/cache-retry) |
| review | Queue, correction, approval-scope and dependency declarations | [Review and change](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/review-change) |
| test | Planned cases, observations, regressions and evidence completeness | [Test and evidence](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/test-evidence) |
| reliability | Component health, incident timelines, alert groups and recovery-evidence readiness | [Reliability and incidents](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/reliability-incident) |
| metrics | Metric definitions, recorded values, span structure and explicit point/span links | [Metrics and traces](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/metrics-traces) |
| documents | Document dependencies, character chunk plans, supplied retrieval scores and exact citations | [Document and answer evidence](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/document-evidence) |
| relational | Schema differences, key integrity, join multiplicity and supplied result checks | [Relational review](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/relational-review) |

The selector installs components and reports installed state; it does not execute
workflows or connect applications. Complete evidence may document a failing test.
PASS describes each tool's contract, not system correctness or release permission.
Keep actual project inputs, output and evidence private; checks do not anonymize data.

Reliability checks assess declarations; they do not probe services or perform recovery.
A valid incident timeline can still describe an unresolved incident.

Metrics/trace checks inspect supplied declarations; they do not collect telemetry,
instrument applications or establish causation. Histogram buckets are disjoint.

Document/evidence checks preserve decoded text pins and code-point offsets.
Exact citation structure does not establish claim support or factual truth.

Relational checks review declarations and supplied rows without opening a database.
Join PASS does not verify key integrity; result PASS does not verify SQL output.
