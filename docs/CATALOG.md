# Public toolkit catalog

The repository brings reusable utilities and neutral development methods into one place. Selected original material is [MIT licensed](../LICENSE). Larger system exports are tracked separately in the [systems roadmap](../systems/README.md).

| Component | Area | Current evidence |
| --- | --- | --- |
| [Dependency Lock Tools](../tools/dependency-lock-tools/README.md) | Dependencies | Recorded Linux fixture results; POSIX requirements |
| [Offline Dependency Lock Diff](../tools/dependency-lock-diff/README.md) | Captured lock comparison | Strict public parser parity, version-text/hash changes and sampled Windows/Ubuntu input guard; 41 local methods, 39 passed and two native-link skips; [review and limits](BATCH-18-LOCK-DIFF.md) |
| [Package Layout Checker](../tools/package-layout-checker/README.md) | Packaging | Preserved POSIX descriptor backend plus Windows native handles; 64 local methods, 27 passed/37 skipped; [platform coverage and limits](BATCH-19-PACKAGE-LAYOUT-WINDOWS.md); declared-file scope |
| [Source Inventory](../tools/source-inventory/README.md) | File evidence | Recorded Linux fixture results; private output |
| [Offline Source Inventory Diff](../tools/source-inventory-diff/README.md) | Captured report comparison | Exact-path metadata classes, coverage/skip/case-fold review and grouped reported hash/size hints; 45 local methods, 43 passed and two native-link skips; [review and limits](BATCH-17-INVENTORY-DIFF.md) |
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
| [Offline Backup Chain Checker](../tools/backup-chain-checker/README.md) | Backup dependency review | Full/incremental relationships, cycle detection and selected ancestry over fictional metadata; 43 local tests, 41 passed and two native-link skips; [review and limits](BATCH-15-BACKUP-CHAINS.md) |
| [Offline Workflow Plan Checker](../tools/workflow-plan-checker/README.md) | Workflow declaration review | Multi-prerequisite cycles, declared state consistency and globally withheld order/eligibility on issues; 46 local tests, 44 passed and two native-link skips; [review and limits](BATCH-16-WORKFLOW-PLANS.md) |
| [Offline Assessment Record Contract Checker](../tools/assessment-record-checker/README.md) | Assessment workflow | Typed record references, same-series later revisions and explicit retest selection; outcomes unverified; [review and limits](BATCH-12-ASSESSMENT-RECORDS.md) |
| [Offline Evaluation Metrics Calculator](../tools/evaluation-metrics-calculator/README.md) | Evaluation arithmetic | Exact ratios from bounded single-label confusion counts, independent undefined metrics and no model execution; [review and limits](BATCH-13-EVALUATION-METRICS.md) |
| [Dataset Review Manager](../systems/dataset-review/README.md) | AI/data systems | New Windows SQLite import, review, deduplication, holdout and export checks; no model calls |
| [Methodology templates](../methodology/README.md) | Engineering and assessment | Neutral templates; no actual approvals or historical records |

See the [sixth-batch review](BATCH-6-REVIEW.md) and [seventh-batch review](BATCH-7-REVIEW.md) for exact execution results. Earlier recorded test results are historical evidence and were not rerun as part of those batches. None of these entries implies blanket platform compatibility, confidentiality clearance or production acceptance.

## Applications added to the shared collection — 2026-10-25

| Application | Runtime / purpose | Validation and limits |
| --- | --- | --- |
| [Local Site Builder](../tools/local-site-builder/README.md) | Node 24 local browser website editor; draft/publish, image uploads, static export and recovery. | 32 generated tests previously passed on Windows/Ubuntu. Collection checks rerun those tests. Loopback local tool; no public CMS deployment or real SMTP acceptance. |
| [Portfolio Builder](../tools/portfolio-builder/README.md) | Python 3.12/3.13 desktop/CLI; structured portfolio site and PDF. | 42 generated tests previously passed across four Windows/Ubuntu/Python jobs. Collection checks rerun those tests. Standard-font PDF/encoding limits apply; no real portfolio included. |
| [Job & Quote Tracker](../tools/job-quote-tracker/README.md) | Python 3.12/3.13, standard library and optional Tk; persistent local jobs, quote history and verified recovery. | 34 local Windows cases discovered: 33 passed, one native symlink privilege skip. Six real Tk cases passed. Collection CI requires Tk on Windows/Ubuntu, Python 3.12/3.13. Operator-entered decision records are not verified signatures or authority. |
| [Offline Assessment Workbench](../tools/assessment-workbench/README.md) | Python 3.12/3.13, standard library and optional Tk; neutral records, private SQLite history, optimistic saves and new-only import/export/clone. | 62 local Windows cases: 60 passed, two native-link skips; all 12 real Tk cases passed. Empty/review drafts stay unverified; logical cloning is not damaged-database repair. See the [review](BATCH-14-ASSESSMENT-WORKBENCH.md). |

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

## ZIP policy, .NET API declarations and ELF hints — 2026-10-25

- [ZIP Package Policy Verifier](../tools/zip-package-policy/README.md) uses a
  user-written, bounded JSON policy to check archive members, expected hashes
  and selected literal text. It does not extract, install or execute a package.
  A matching policy does not establish authenticity or absence of malware.
- [.NET Public API Diff](../tools/dotnet-api-diff/README.md) reads trusted managed
  build metadata, compares supported public declarations and explains changes.
  No target assembly is loaded or executed. Declaration comparisons do not
  establish full source/binary compatibility, and hostile assemblies are outside
  the supported trust boundary of the underlying metadata parser.
- [ELF Runtime Reference Hints](../tools/offline-elf-inspector/README.md) adds an
  opt-in bounded string scan. Hints stay separate from declared `DT_NEEDED`
  dependencies and do not prove runtime use, missing dependencies or loader behavior.

The batch uses newly authored fixtures and generated ZIP, DLL and ELF inputs.
Module validation notes and GitHub Actions record the Windows/Ubuntu checks.
Real package contents, assemblies, firmware, embedded paths and inspection
reports belong in a separate private workspace. Original local helper files
remain intact; device-specific commands and payloads are not public examples.

## Saved capture logs, VPD references and inventory rules — 2026-10-25

- [FFmpeg Capture Log Inspector](../tools/ffmpeg-log-inspector/README.md) reads
  bounded saved text, summarizes supported progress observations and identifies
  selected diagnostic markers. It does not invoke FFmpeg, record video or access
  devices. Log progress and absence of recognized errors do not prove playable
  output, capture quality, completeness or a hardware root cause.
- [VPD Media Reference Checker](../tools/vpd-reference-checker/README.md) reads
  a supported subset of VideoProc Vlogger project JSON. It distinguishes selected
  resource references from project-record and unclassified path fields. Optional
  checks use explicit mappings to safe relative copies under a selected local
  root, with metadata only. Embedded paths are not followed automatically. This
  is not editor compatibility, media validation or a complete project backup.
- [Source Inventory Rule Classifier](../tools/source-inventory/README.md) consumes
  existing inventory CSV/summary files, checks their recorded contract, then
  applies user-defined exact/prefix/suffix rules with explicit case handling.
  Reports show the first match, every matching rule, overlaps and unmatched paths.
  Inventoried file bodies are not reopened. Categories are user policy, not
  authorship, license, safety, backup or publication clearance.

The local original helpers remain unchanged. Public examples are generated;
real project documents, recordings, capture logs, inventories, private paths and
device-specific recipes remain outside the source export. Read each module's
provenance and validation record, and check Windows/Ubuntu CI results. Runtime
and operating-system observations are distinct from supported parser fixtures.

## Git worktrees, PDF text bounds and SVG references — 2026-10-25

- [Git Worktree Review Reporter](../tools/git-worktree-reporter/README.md) reads
  supported local status and stored branch relationships through an explicitly
  selected trusted Git executable. It uses an isolated policy and rejects
  unsupported configuration; that policy can differ from a user's usual Git
  settings. It does not fetch, push, commit, check out files or create backups.
  Stored upstream refs may be stale. Reports can identify private work and must
  not be treated as complete recovery, ownership or publication clearance.
- [PDF Text Bounds Inspector](../tools/pdf-text-bounds/README.md) checks bounded
  observed glyph geometry in trusted completed PDFs through a time-limited
  worker. The documented page-box, rotation and tolerance semantics matter.
  It does not establish readable text, visual quality, complete clipping
  detection, image/shape coverage or safety of arbitrary hostile PDFs.
- [SVG Content & Reference Inspector](../tools/svg-content-inspector/README.md)
  inspects a bounded static subset using an updated XML parser. Declared
  dimensions, active-content signals, internal fragments and external/uncertain
  references remain distinct. Unsupported CSS and syntax require review.
  No referenced resource is opened or fetched, and input SVG is never rendered
  in the report. This is not a sanitizer or a universal rendering-safety verdict.

The public source contains authored fixtures rather than real repositories,
documents or artwork. Local original helpers remain unchanged. Tests use
disposable repositories and generated PDF/SVG data; actual parser/subprocess
tests, visual checks of generated fixtures and source-only checks are separate
evidence types. Read module validation records and Windows/Ubuntu CI results.
Python/runtime security requirements and separately licensed PDF dependencies
are part of the supported setup; dependency pins are not a general safety proof.

## Android and Linux configuration review — 2026-10-25

- [Android Init Service Inspector](../tools/android-init-inspector/README.md):
  literal selected-file service/action index, duplicate declarations,
  reboot-related markers and selected-reference resolution. Imports and
  properties are never followed/evaluated; unresolved references do not prove
  services are missing from a complete device configuration.
- [Android Build Copy-Map Inspector](../tools/android-copy-map-inspector/README.md):
  literal PRODUCT_COPY_FILES append candidates, explicitly supplied root
  substitutions and declared destination/case/parent collisions. Make
  assignments, functions, conditionals, source availability and payload rights
  are not evaluated. Collision observations are not an effective build verdict.
- [Fstab Configuration Diff](../tools/fstab-diff/README.md):
  explicit Linux/Android modes, supported field changes and relative order of
  unique common targets. Duplicate targets remain ambiguous without arbitrary
  pairing; options remain ordered text rather than evaluated mount semantics.

All three are original MIT standard-library Python source with bounded UTF-8
inputs, fresh private JSON/HTML reports, source manifests, generated examples,
Windows/Ubuntu tests and dedicated bug/suggestion forms. This source release
contains no original private config or vendor/firmware payload. No successful
build, boot, mount or hardware recovery is claimed.

## Disk-image, module and VINTF metadata inspectors — 2026-10-25

- [Offline GPT Disk Image Inspector](../tools/gpt-image-inspector/README.md):
  bounded regular-file raw-image metadata reads, explicit sector selection,
  supported header/table CRCs, partition-range signals and primary/backup
  observations. No physical drive, payload scan, whole-image hash or repair.
- [Kernel Module List & Dependency Inspector](../tools/kernel-module-inspector/README.md):
  documented text snapshot grammar, declared name/dependency ambiguity, cycle
  witnesses and selected dependency-first ordering. Optional membership is a
  caller-declared text inventory. No native kmod, binary, builtin or ABI inference.
- [Android VINTF Manifest Inspector](../tools/vintf-manifest-inspector/README.md):
  original bounded restricted XML reading, supported HIDL/AIDL declaration index and selected
  comparison. Duplicate keys are ambiguous; modifiers/unsupported grammar are
  coverage. No effective merge, compatibility-matrix or runtime service check.

Each has original MIT source, detailed guides, generated examples, exact source
manifests and dedicated bug/suggestion forms. Default field omission is not
anonymization. [Review and test boundaries](PLATFORM-INSPECTORS-REVIEW-2026-10-25.md)
distinguish generated metadata tests from real device/runtime evidence.

## Saved events, properties and filesystem metadata — 2026-10-25

- [Windows Event Timeline Inspector](../tools/windows-event-timeline/README.md):
  selected saved JSON/restricted XML metadata, exact 100 ns timestamp arithmetic,
  grouped counts and scoped record-ID/gap observations. Relative times by
  default, selected fields opt-in, computer/payload fields always omitted.
  No live query, binary EVTX decoding, completeness or causal diagnosis.
- [Android Property Configuration Diff](../tools/android-property-diff/README.md):
  literal selected .prop declarations; duplicate keys are ambiguous, imports
  unfollowed and unidentified rows prevent unsupported unmatched claims.
  No effective property merge, permissions, reserved-key or runtime evaluation.
- [Filesystem Permission Manifest Diff](../tools/permission-manifest-diff/README.md):
  declared path/UID/GID/octal mode/optional label and capability changes. Unknown
  fields retain known paths as held; unknown identities hold opposite unmatched
  candidates. No target lookup, actual access/policy evaluation or chmod/chown.

All have original MIT source, detailed guides, generated examples, exact source
inventories and dedicated bug/suggestion forms. Read the
[review and test boundaries](EVENT-CONFIG-REVIEW-2026-10-25.md). Real inputs and
identifying reports remain private; generated findings are limited observations.
