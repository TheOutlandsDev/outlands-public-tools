# OUTLANDS public project map

[Profile](https://github.com/TheOutlandsDev) Â· [Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools) Â· [Game Tools](https://github.com/TheOutlandsDev/outlands-game-tools)

Choose a project by what you want to do. Each repository has its own setup, dependency, license and validation requirements; a link between projects does not establish compatibility.

## How tools support a system

The [published model-routing wheels](../integrations/model-routing/README.md) provide four small checks that a Python project can install separately or together. Their [component guide](../integrations/model-routing/components.json) describes exact entry points and examples for human or AI-assisted discovery. The [Corpus & Model Workbench](../systems/corpus-model-workbench/README.md) is a related local application with its own model workflow. The integration guide documents a possible boundary between the checks and that application; no adapter is installed in the Workbench.

The [AI decision-contract wheels](../integrations/ai-decision-contracts/README.md) give four more independent and collection install choices for prompt interfaces, label mappings, score abstention policies and candidate review gates. Their [component guide](../integrations/ai-decision-contracts/components.json) states exact input/result formats and limits. The [install plan](../integrations/INSTALL-PLAN.md) records distribution and documentation status for all public tools; the AI tools do not install an adapter into the related workbenches.

The [task-to-system map](TOOL-TO-SYSTEM-MAP.md) shows representative connections across the collection and other OUTLANDS projects. Choose a task, identify the smallest useful tool, show its input and result, then link to a system that could use it. [Terms and evidence levels](../methodology/TERMS.md) keep those relationships precise.

## Apps & developer tools

The [thirty-six-tool install bundle](../integrations/public-tools-bundle-36/START-HERE.md) combines the nine reviewed Python cohorts into one selectable download. It includes install choices and component contracts; the workbench connections above remain documented use cases without installed adapters.

The [probability integrity tools](../integrations/probability-integrity/README.md) add exact probability checks, error and reliability summaries, and map revision review. The guide explains the possible connection to ML Experiment Workbench and the decimal conversion policy a future adapter must define.

The [cache and retry guide](../integrations/cache-retry/README.md) adds key/freshness review, attempt-policy checks and operation-claim reconciliation. It explains a possible connection to the Data & Services Stack while preserving unknown outcomes and distinct namespaces.

The [review/change guide](../integrations/review-change/README.md) adds correction-chain, queue, approval-scope and impact review. It documents a possible connection to Assessment & Evidence Workbench with explicit identity, policy and dependency mappings.

The [test/evidence guide](../integrations/test-evidence/README.md) adds independent packages, plain-language definitions and an installed case-to-evidence exercise. Its Test & Evidence Workbench use case requires explicit mappings; complete evidence does not upgrade a failed test.

The [reliability/incident guide](../integrations/reliability-incident/README.md) adds independent packages, precise definitions and an installed health-to-recovery exercise. Its Reliability & Incident Workbench use case requires explicit time, identity and policy mappings; a valid timeline does not imply resolution or recovery readiness.

The [metrics/trace guide](../integrations/metrics-traces/README.md) adds individual packages, plain-language definitions and an installed fictional metric-to-span exercise. Its Data & Services Stack use case requires explicit metric, run, clock and span mappings; a consistent link does not establish causation or actual telemetry.

The [document/evidence guide](../integrations/document-evidence/README.md) adds individual packages, exact Python operation names, plain-language definitions and an installed document-to-citation example. Its Corpus & Model Workbench use case requires explicit text, revision, hash-domain, ranking/judgment and citation mappings; structural citation PASS does not establish claim support or factual truth.

[Full shared tool catalog](../catalog/generated/INDEX.md) Â· [Current downloads](../packages/README.md) Â· [Methodology workshops](../workshops/README.md)

| Repository | Role | Start here |
| --- | --- | --- |
| [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools) | Maintained collection for local apps and reusable engineering utilities. | [Application catalog](https://github.com/TheOutlandsDev/outlands-public-tools#applications-in-this-collection) |
| [workfloor](https://github.com/TheOutlandsDev/workfloor) | Synthetic manufacturing and SQL reporting application. | [Source, samples and v0.2 download](https://github.com/TheOutlandsDev/workfloor) |
| [code-atlas](https://github.com/TheOutlandsDev/code-atlas) | Local VS Code language map and read-only source navigation. | [Setup](https://github.com/TheOutlandsDev/code-atlas/blob/main/docs/setup-r2.md) |
| [outlands-local-site-builder](https://github.com/TheOutlandsDev/outlands-local-site-builder) | Earlier standalone Site Builder source and history. | [Maintained collection folder](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/local-site-builder) |
| [outlands-portfolio-builder](https://github.com/TheOutlandsDev/outlands-portfolio-builder) | Earlier standalone Portfolio Builder source and history. | [Maintained collection folder](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/portfolio-builder) |

## Games & modding

| Repository | Role | Start here |
| --- | --- | --- |
| [outlands-game-tools](https://github.com/TheOutlandsDev/outlands-game-tools) | Reusable inspectors, diagnostics, save utilities and SPT mod source. | [Getting started](https://github.com/TheOutlandsDev/outlands-game-tools/blob/main/docs/GETTING-STARTED.md) |
| [outlands-spt-modpack](https://github.com/TheOutlandsDev/outlands-spt-modpack) | Matching Outlands SPT Client/SelfHost setup and player updater. | Current README and compatibility record; public source/downloads do not grant host access. |
| [outlands-bo2-mod](https://github.com/TheOutlandsDev/outlands-bo2-mod) | Private BO2 play, native bots, progression and optional local model chat. | Platform setup and validation notes in the README. |
| [gamma-clearsky-warfare](https://github.com/TheOutlandsDev/gamma-clearsky-warfare) | Clear Sky Warfare presets/addons and experimental co-op launcher source. | [Installation and safe tests](https://github.com/TheOutlandsDev/gamma-clearsky-warfare/blob/main/docs/INSTALL.md) |
| [iw4x-bot-warfare-extras](https://github.com/TheOutlandsDev/iw4x-bot-warfare-extras) | Bot Warfare extensions, presets and local learning utilities. | [Command reference](https://github.com/TheOutlandsDev/iw4x-bot-warfare-extras/blob/main/COMMANDS.md) |
| [outlands-state-of-decay-2-qol](https://github.com/TheOutlandsDev/outlands-state-of-decay-2-qol) | Experimental State of Decay 2 setup recipes and source tools. | README; separate author downloads are required. |

## Infrastructure & protocol research

| Repository | Role | Start here |
| --- | --- | --- |
| [outlands-private-workspace-blueprint](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint) | Public Homepage/Docker/Tailscale reference guide and theme examples. | [Build path](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/blob/main/docs/02-build-path.md) |
| [outlands-protocol](https://github.com/TheOutlandsDev/outlands-protocol) | Rust encoding, state, consensus, storage and P2P research source. | README and validation scope; no deployed network or production wallet claimed. |

## Where to ask for help

Use the relevant repository's Issues tab. For maintained Site Builder and Portfolio Builder additions, use the [Public Tools issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose). Include the version, a small reproduction and the result you expected. Keep private input data and access details out of public reports.

This map covers public repositories reviewed on 2026-10-26. Release numbers and detailed test results stay with their owning repositories so the map can link to current information.
