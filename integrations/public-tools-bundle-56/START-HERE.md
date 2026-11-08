# OUTLANDS fifty-six-tool install bundle

This ZIP contains fifty-six independent MIT Python tool wheels, fourteen group
installers and selector v1.12.0. Supply Python 3.12 or 3.13 and pip separately.
COMPONENTS.json describes purposes, use cases, APIs, formats and limits. No runtime,
real inputs, private records, profiles, logs or application adapters are included.

Download the ZIP and outer SHA256SUMS.txt from the same
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.12.0).
Verify the ZIP SHA-256 before extracting into a new folder outside the checkout.
Inner SHA256SUMS.txt pins all seventy-one wheels; MANIFEST.json pins every other
archive member. Create a fresh environment outside that extracted folder with
`py -3.12 -m venv ../ENV` on Windows or `python3.12 -m venv ../ENV` on Ubuntu.
From the extracted root, use that environment's Python:

```text
python -m pip install --no-index --no-deps wheels/outlands_api_request_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[routing]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ai]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[probability]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[cache]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[review]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[test]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[reliability]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[metrics]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[documents]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[relational]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ingestion]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[workers]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[configuration]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[api]==1.12.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[all]==1.12.0"
```

The first installs one tool; substitute any individual filename from COMPONENTS.json.
Other choices install one four-tool group or all fifty-six. On PowerShell use
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
| ingestion | Mapping differences, advisory replay plans, checkpoint coverage and declared run totals | [Ingestion control](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/ingestion-control) |
| workers | Work-item interfaces, declared lease ownership, acknowledgement accounting and result/commit bindings | [Worker and queue review](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/worker-queue) |
| configuration | Fingerprint-only overlays, field-metadata differences, requested pair rules and supplied migration paths | [Configuration review](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/configuration-review) |
| api | Operation definitions, supplied requests/responses and selected-case version comparison | [API request-and-response review](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/integrations/api-exchange) |

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

Ingestion checks review supplied declarations. No import, retry or checkpoint write is performed or authorized. Receipt authority, source counts and exactly-once execution are not verified.

Worker/queue checks inspect declarations without opening payloads/artifacts or contacting workers/brokers. They do not enforce ownership, execute jobs, send acknowledgements or commit results.

Configuration review uses supplied metadata and opaque fingerprints. It does not validate actual settings, prove runtime compatibility, open adapters or execute migrations.

API exchange checks review bounded supplied operation/request/response declarations. A response PASS can describe an error and a comparison PASS can describe equal negative cases. No endpoint, authentication, wire protocol or whole-service behavior is verified.
