# Public toolkit catalog

The repository brings reusable utilities and neutral development methods into one place. Selected original material is [MIT licensed](../LICENSE). Larger system exports are tracked separately in the [systems roadmap](../systems/README.md).

| Component | Area | Current evidence |
| --- | --- | --- |
| [Dependency Lock Tools](../tools/dependency-lock-tools/README.md) | Dependencies | Recorded Linux fixture results; POSIX requirements |
| [Package Layout Checker](../tools/package-layout-checker/README.md) | Packaging | Recorded Linux fixture results; declared-file scope |
| [Source Inventory](../tools/source-inventory/README.md) | File evidence | Recorded Linux fixture results; private output |
| [XML Recipe Inspector](../tools/xml-recipe-inspector/README.md) | Structured input | Recorded Linux fixture results; retained schema conventions |
| [Markdown Document Builder](../tools/document-builders/README.md) | Documents | Recorded Linux fixture results; declared third-party dependency |
| [Safe File Mover](../tools/safe-file-mover/README.md) | File operations | Recorded fixture results; native/GUI/SMB limitations |
| [Keep Awake](../tools/keep-awake/README.md) | Desktop | Recorded simulated tests; native acceptance unverified |
| [Public Release Audit](../tools/public-release-audit/README.md) | Release hygiene | New Windows fixture checks; text export scope |
| [Project Workspace](../tools/project-workspace/README.md) | Project setup | New Windows disposable creation/copy checks |
| [Documentation Check](../tools/documentation-check/README.md) | Documentation | New Windows fixture checks; partial Markdown grammar |
| [Python Helpers](../tools/python-helpers/README.md) | Programming | New Windows unit checks; limited structured redaction |
| [Verified source packages and private data handoffs](../tools/verified-transfers/README.md) | Source release and private data | Hash-pinned explicit source copy; opaque local snapshot/restore; no app-stop verification |
| [Server Maintenance Planner](../tools/server-maintenance/README.md) | Server operations | Offline calendar, lifecycle and readiness rules; no service control |
| [Release Preflight](../tools/release-preflight/README.md) | Update and launcher review | Pinned local inventory, selected-file update plan and static launcher checks; 26 Windows fixture methods passed, 2 native link skips |
| [Environment Contract Checker](../tools/environment-contract-checker/README.md) | Setup prerequisites | Explicit metadata checks and unverified observations; fictional Windows tests and Windows/Ubuntu CI; [review and limits](BATCH-9-ENVIRONMENT-CONTRACT.md) |
| [Connection Plan Checker](../tools/connection-plan-checker/README.md) | Local connection planning | Strict loopback declaration checks and bounded conflict groups; no listener inspection or runtime availability proof; [review and limits](BATCH-9-CONNECTION-PLAN.md) |
| [Offline Configuration Contract Checker](../tools/configuration-contract-checker/README.md) | Configuration review | Flat scalar settings, strict declared constraints and blocked dependency rules; no live acceptance; [review and limits](BATCH-10-CONFIGURATION-CONTRACT.md) |
| [Backup Retention Planner](../tools/backup-retention-planner/README.md) | Backup policy review | Count/age/pin union, cutoff ties and future-date review for declared independent full snapshots; no deletion; [review and limits](BATCH-11-BACKUP-RETENTION.md) |
| [Dataset Review Manager](../systems/dataset-review/README.md) | AI/data systems | New Windows SQLite import, review, deduplication, holdout and export checks; no model calls |
| [Methodology templates](../methodology/README.md) | Engineering and assessment | Neutral templates; no actual approvals or historical records |

See the [sixth-batch review](BATCH-6-REVIEW.md) and [seventh-batch review](BATCH-7-REVIEW.md) for exact execution results. Earlier recorded test results are historical evidence and were not rerun as part of those batches. None of these entries implies blanket platform compatibility, confidentiality clearance or production acceptance.

## Applications added to the shared collection — 2026-10-25

| Application | Runtime / purpose | Validation and limits |
| --- | --- | --- |
| [Local Site Builder](../tools/local-site-builder/README.md) | Node 24 local browser website editor; draft/publish, image uploads, static export and recovery. | 32 generated tests previously passed on Windows/Ubuntu. Collection checks rerun those tests. Loopback local tool; no public CMS deployment or real SMTP acceptance. |
| [Portfolio Builder](../tools/portfolio-builder/README.md) | Python 3.12/3.13 desktop/CLI; structured portfolio site and PDF. | 42 generated tests previously passed across four Windows/Ubuntu/Python jobs. Collection checks rerun those tests. Standard-font PDF/encoding limits apply; no real portfolio included. |
| [Job & Quote Tracker](../tools/job-quote-tracker/README.md) | Python 3.12/3.13, standard library and optional Tk; persistent local jobs, quote history and verified recovery. | 34 local Windows cases discovered: 33 passed, one native symlink privilege skip. Six real Tk cases passed. Collection CI requires Tk on Windows/Ubuntu, Python 3.12/3.13. Operator-entered decision records are not verified signatures or authority. |

The applications have separate source manifests and dependency notices. Test fixtures are fictional. Their generated outputs and working stores are private application data, not source intended for GitHub. See the [application review](APPLICATIONS-2026-10-25.md).

## Offline ELF Dependency Inspector — 2026-10-25

[Offline ELF Dependency Inspector](../tools/offline-elf-inspector/README.md) is a
fresh portable public implementation based on the owner's local phone dependency
analysis workflow. Python 3.12/3.13 standard library only, Windows/Linux CLI and
offline HTML/JSON reports. It never executes inspected files or connects to a
device. ELF32/ELF64 metadata, both byte orders, conservative candidate graphs and
coverage issues are supported; OS loader emulation and complete ABI compatibility
are outside scope. Original firmware, paths, seed lists and identifiers are excluded.

Local Windows: 50 discovered tests, 48 passed and two documented skips. The
separate inspector workflow tests Windows/Ubuntu Python 3.12/3.13 and requires a
Linux GCC/readelf comparison using generated original libraries. See its
[validation record](../tools/offline-elf-inspector/docs/VALIDATION.md) and current
Actions results. No phone, firmware or production runtime acceptance is claimed.

## Friendlies — experimental source preview — 2026-10-25

[Friendlies](../tools/friendlies/README.md) rewrites an existing local SPT draft as
an original MIT core, typed adapter, diagnostic UI and idle follow layer. It is
source only, disabled by default, and blocks Fika spawning. The compile-reference
target is SPT 4.0.13 / EFT 0.16.9.40087 with BigBrain 1.4.0. No game/dependency DLL,
profile, private SDK report or compiled product is distributed.

The local matching-SDK build had zero warnings/errors; 62 pure core fixtures pass.
Separate Windows/Ubuntu CI covers the core/source gate, not the game adapter or
Unity. **No gameplay is verified.** The owner chose source-only publication without
a clean solo installation. Follow the module's pending gameplay plan before any
runtime qualification; SAIN/other AI mods and each faction need separate tests.

## Steven Chat (Stephen) — 2026-10-25

[Steven Chat](../tools/steven-chat/README.md) rebuilds the owner's duplicate local
chatbot draft into a Python 3.12/3.13 standard-library terminal client. It supports
a network-free simulated demo, explicit loopback Ollama connections, whole-pair
context trimming, model selection and optional new-file session saves. The
legacy Stephen name is documented and kept as an entry-point alias.

No server/model is installed, started, downloaded or bundled. The Ollama server
must be configured separately to disable cloud features before sensitive use;
loopback restriction alone cannot enforce the server's outbound behavior.
Automated tests use generated data and a loopback HTTP fixture, not a language
model. Real-model inference, model quality and hardware performance remain
unverified. Read the module's validation and privacy limits before live use.

## App Affinity Launcher — 2026-10-25

[App Affinity Launcher](../tools/app-affinity-launcher/README.md) generalizes a
local game-specific command wrapper into an original Python 3.12/3.13 standard-
library utility. Demo and preview modes do not start the selected program.
Explicit Windows launch creates a process suspended, applies and reads back the
requested CPU affinity and normal priority, then resumes its primary thread.
It accepts explicit local executable/working-directory paths and literal
arguments, with no command shell, installer or persistent affinity setting.

Execution is limited to supported single-processor-group Windows systems. The
duplicate check is best effort; it cannot prove absence of inaccessible or
concurrently starting processes. Receipts establish launcher setup, not target
application usability, performance or gameplay. Tests use generated programs,
portable fake backends and actual disposable Windows children; Ubuntu covers
portable policy and refuses live Windows execution. See the module's validation
record and current CI results. Original game files and private records are excluded.

## Folder trees, Resource Monitor and Hash Journal — 2026-10-25

- [Source Inventory](../tools/source-inventory/README.md) adds an optional bounded,
  readable folder-tree export to its existing selected-file hash inventory.
  Tree coverage, exclusions, depth limits and filename escaping are explicit.
- [Resource Monitor](../tools/resource-monitor/README.md) is an original Python
  API and first-party HTML/CSS/JavaScript dashboard for aggregate local metrics.
  It has explicit demo/live modes, bounded in-memory history and opt-in exports.
  The historical packet-monitor source remains held privately and was not copied.
- [Hash Journal](../tools/hash-journal/README.md) is an original .NET 8 C# CLI for
  bounded JSONL hash chains and fresh snapshot outputs. Verification against an
  externally retained expected head can detect chain changes; unanchored local
  hashes alone do not establish authenticity or protect a rewritten/truncated chain.

Read each module's test record and current CI results. The batch's Python and
JavaScript checks run on Windows/Ubuntu with Python 3.12/3.13 and Node 24; C#
fixtures run with .NET 8 on Windows/Ubuntu. Generated fixtures, actual loopback
HTTP checks and explicitly recorded native sampling are separate evidence types.
Real directory reports, machine metrics, event records and old project data
remain outside the public source export. See the [skills map](SKILLS-MAP.md).
