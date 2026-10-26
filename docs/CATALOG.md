# Public toolkit catalog

The repository brings reusable utilities and neutral development methods into one place. Selected original material is [MIT licensed](../LICENSE). Larger system exports are tracked separately in the [systems roadmap](../systems/README.md).

| Component | Area | Current evidence |
| --- | --- | --- |
| [Dependency Lock Tools](../tools/dependency-lock-tools/README.md) | Dependencies | Preserved POSIX bodies and strict parsers plus Windows native reads/exclusive output; [platform review and limits](BATCH-20-DEPENDENCY-LOCK-WINDOWS.md); inherited Windows ACLs |
| [Offline Dependency Lock Diff](../tools/dependency-lock-diff/README.md) | Captured lock comparison | Strict public parser parity, version-text/hash changes and sampled Windows/Ubuntu input guard; 41 local methods, 39 passed and two native-link skips; [review and limits](BATCH-18-LOCK-DIFF.md) |
| [Package Layout Checker](../tools/package-layout-checker/README.md) | Packaging | Preserved POSIX descriptor backend plus Windows native handles; 64 local methods, 27 passed/37 skipped; [platform coverage and limits](BATCH-19-PACKAGE-LAYOUT-WINDOWS.md); declared-file scope |
| [Source Inventory](../tools/source-inventory/README.md) | File evidence | Preserved POSIX/report/classifier contracts plus native Windows guards; [review and limits](BATCH-25-SOURCE-INVENTORY-WINDOWS.md); real reports stay private |
| [Offline Source Inventory Diff](../tools/source-inventory-diff/README.md) | Captured report comparison | Exact-path metadata classes, coverage/skip/case-fold review and grouped reported hash/size hints; 45 local methods, 43 passed and two native-link skips; [review and limits](BATCH-17-INVENTORY-DIFF.md) |
| [XML Recipe Inspector](../tools/xml-recipe-inspector/README.md) | Structured input | Preserved POSIX/XML/CSV logic plus Windows native inputs/new-directory reports; [platform review and limits](BATCH-21-XML-RECIPE-WINDOWS.md); retained schema conventions |
| [Markdown Document Builder](../tools/document-builders/README.md) | Documents | Preserved parser/layout/Linux I/O plus Windows native file checks and fictional DOCX package inspection; [review and limits](BATCH-22-DOCUMENT-BUILDER-WINDOWS.md); declared third-party dependency |
| [Safe File Mover](../tools/safe-file-mover/README.md) | File operations | Windows native CLI/engine and generated recovery/ADS fixtures; preserved Linux protections; [review and limits](BATCH-23-FILE-MOVER-WINDOWS.md); GUI/live-SMB acceptance separate |
| [Keep Awake](../tools/keep-awake/README.md) | Desktop | 56 local methods passed, including 15 opt-in native Windows request/Tk cases; [review and limits](BATCH-24-KEEP-AWAKE-WINDOWS.md); actual idle sleep/policy acceptance separate |
| [Public Release Audit](../tools/public-release-audit/README.md) | Release hygiene | Preserved detector/POSIX export/report bodies plus bounded controls and native Windows I/O; [review and limits](BATCH-26-PUBLIC-AUDIT-WINDOWS.md); reports private |
| [Project Workspace](../tools/project-workspace/README.md) | Project setup | Preserved POSIX/plan behavior plus native Windows directory, input and exclusive output guards; [review and limits](BATCH-27-PROJECT-WORKSPACE-WINDOWS.md); generated workspaces private |
| [Documentation Check](../tools/documentation-check/README.md) | Documentation | Preserved grammar/POSIX link guards with bounded I/O and native Windows target metadata checks; [review and limits](BATCH-28-DOCUMENTATION-CHECK-HARDENING.md); reports private |
| [Python Helpers](../tools/python-helpers/README.md) | Programming | Preserved JSON/redaction rules with checked Windows/POSIX ordinary-file reads; [review and limits](BATCH-29-PYTHON-HELPERS-HARDENING.md); outputs private |
| [Verified source packages and private data handoffs](../tools/verified-transfers/README.md) | Source release and private data | Hash-pinned explicit source copy; opaque local snapshot/restore; no app-stop verification |
| [Server Maintenance Planner](../tools/server-maintenance/README.md) | Server operations | Offline calendar, lifecycle and readiness rules with guarded Windows/POSIX inputs; no service control |
| [Release Preflight](../tools/release-preflight/README.md) | Update and launcher review | Pinned local inventory, selected-file update plan and static launcher checks; 26 Windows fixture methods passed, 2 native link skips |
| [Environment Contract Checker](../tools/environment-contract-checker/README.md) | Setup prerequisites | Explicit metadata checks and unverified observations; fictional Windows tests and Windows/Ubuntu CI; [review and limits](BATCH-9-ENVIRONMENT-CONTRACT.md) |
| [Connection Plan Checker](../tools/connection-plan-checker/README.md) | Local connection planning | Strict loopback declaration checks and bounded conflict groups; no listener inspection or runtime availability proof; [review and limits](BATCH-9-CONNECTION-PLAN.md) |
| [Offline Configuration Contract Checker](../tools/configuration-contract-checker/README.md) | Configuration review | Flat scalar settings, strict declared constraints and blocked dependency rules; no live acceptance; [review and limits](BATCH-10-CONFIGURATION-CONTRACT.md) |
| [Backup Retention Planner](../tools/backup-retention-planner/README.md) | Backup policy review | Count/age/pin union, cutoff ties and future-date review for declared independent full snapshots; no deletion; [review and limits](BATCH-11-BACKUP-RETENTION.md) |
| [Offline Backup Chain Checker](../tools/backup-chain-checker/README.md) | Backup dependency review | Full/incremental relationships, cycle detection and selected ancestry over fictional metadata; 43 local tests, 41 passed and two native-link skips; [review and limits](BATCH-15-BACKUP-CHAINS.md) |
| [Offline Workflow Plan Checker](../tools/workflow-plan-checker/README.md) | Workflow declaration review | Multi-prerequisite cycles, declared state consistency and globally withheld order/eligibility on issues; 46 local tests, 44 passed and two native-link skips; [review and limits](BATCH-16-WORKFLOW-PLANS.md) |
| [Offline Assessment Record Contract Checker](../tools/assessment-record-checker/README.md) | Assessment workflow | Typed record references, same-series later revisions and explicit retest selection; outcomes unverified; [review and limits](BATCH-12-ASSESSMENT-RECORDS.md) |
| [Offline Evaluation Metrics Calculator](../tools/evaluation-metrics-calculator/README.md) | Evaluation arithmetic | Exact ratios from bounded single-label confusion counts, independent undefined metrics and no model execution; [review and limits](BATCH-13-EVALUATION-METRICS.md) |
| [Dataset Review Manager](../systems/dataset-review/README.md) | AI/data systems | Checked JSONL and canonical legacy store/schema acceptance; review/deduplication/holdouts preserved; [current review and limits](BATCH-31-DATASET-STORE-SCHEMA.md); stores/exports private |
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
  The historical packet-monitor source was not copied into Resource Monitor.
  Its separately reviewed owner-confirmed adaptation is now Desktop Network Monitor below.
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

## Android images and saved package declarations — 2026-10-26

- [Android Sparse Image Inspector](../tools/android-sparse-inspector/README.md):
  supported sparse structure and declared size/range observations without expansion.
- [Boot / Vendor Boot Header Inspector](../tools/android-boot-inspector/README.md):
  supported v3/v4 header/component layout observations without payload extraction.
- [APK Metadata Report Diff](../tools/apk-report-diff/README.md): supported saved
  AAPT2 badging declarations, explicit ambiguities and private metadata comparison.

All have original MIT source, detailed instructions, synthetic examples, reviewed
source inventories and dedicated bug/suggestion forms. Read the
[review and validation boundaries](ANDROID-IMAGES-REVIEW-2026-10-26.md). Generated
fixture validation is separate from real-firmware acceptance, bootability, signature
verification, installability and effective runtime state. Actual images, APKs and
identifying reports stay private.

## Saved telemetry, binary plans and Android build declarations — 2026-10-26

- [Offline Session Telemetry Analyzer](../tools/session-telemetry-analyzer/README.md):
  supported JSONL samples, explicit per-metric denominators and coverage; no live
  collection, unique-player inference, causal diagnosis or completeness proof.
- [Verified Binary Patch Planner](../tools/binary-patch-planner/README.md): verified
  source/expected bytes and declared edits, preview by default, separate fresh
  output only when explicitly requested; no game-specific patch recipes.
- [Android Build Module Declaration Inspector](../tools/android-build-module-inspector/README.md):
  selected literal build declarations, repeated-name observations and conservative
  requested-name scope; no Make/Soong execution or effective build evaluation.

All include original MIT source, detailed instructions, synthetic examples, exact
source inventories and dedicated bug/suggestion forms. Read the
[review and validation boundaries](SESSION-PATCH-BUILD-REVIEW-2026-10-26.md).
Private telemetry, real patch plans/assets and vendor configuration stay private.

## Managed mod-profile workspaces — 2026-10-26

[Mod Profile Activation Manager](../tools/mod-profile-manager/README.md) adds
named profile imports, a stable managed active folder, read-only previews,
verification/drift review, retained previous trees and interruption recovery.
CLI and optional Tk desktop use the same bounded engine. It manages its own
workspace; game integration is manual and game-dependent. No game detection,
live installation, asset distribution, automatic purge or save management.

Read the [source review and evidence limits](PROFILE-MANAGER-REVIEW-2026-10-26.md).
Original MIT source, detailed instructions, generated examples and dedicated
bug/suggestion forms are included. Runtime stores and actual profiles stay private.

## USB presence observations — 2026-10-26

[USB Connection Monitor](../tools/usb-connection-monitor/README.md) adds explicit
selected-instance Windows PnP polling, a readable idle-start Tk desktop,
bounded query cancellation, fictional demos and offline neutral-sample replay.
Failed queries stay unknown; reports omit identity fields and raw native data.
Selection lists are private and exact IDs are chosen explicitly. Polling can
miss changes and establishes neither physical identity nor a failure's cause.
No camera/audio capture, device reset, driver/power change or upload feature.

Original MIT source includes detailed guides, generated examples/tests and
dedicated feedback forms. Read the [review](USB-MONITOR-REVIEW-2026-10-26.md)
for local/native/CI evidence and physical-device acceptance limits.

## Desktop IPv4 packet observations — 2026-10-26

[Desktop Network Monitor](../tools/desktop-network-monitor/README.md) adapts the
owner-confirmed existing desktop monitor into offline demo/replay, local rules,
idle-start Tk, explicit bounded capture and manual OTX observations. It fixes
automatic capture/lookup/logging, incomplete address filtering, nested-header
port borrowing and conflated malware/packet counts. No real traffic or key is
included. Own source is MIT; optional dependencies keep their separate licenses,
including Scapy GPL-2.0-only. No combined runtime/driver distribution is offered.

[The review](NETWORK-MONITOR-REVIEW-2026-10-26.md) distinguishes actual installed
offline decoding, native Tk, owned-child shutdown and system-counter checks from
unqualified live interface/Npcap and external-service acceptance. Dedicated forms
welcome fictional bug reports and suggestions. Aggregate reports omit identity
fields but are not anonymous or complete traffic/security evidence.
