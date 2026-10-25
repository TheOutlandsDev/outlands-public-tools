# Engineering skills represented by the collection

Use the source, examples and tests below to assess specific mechanisms. This is
an implementation map, not a claim that fixture tests establish every production
workflow, target application or deployment. Original work and documentation were
developed with AI assistance; dependencies retain their authors' credits and terms.

| Language or layer | Concrete code and behavior | Review and evidence |
| --- | --- | --- |
| Python / filesystems | [Source Inventory](../tools/source-inventory/README.md): bounded traversal, selected-file SHA-256, deterministic exports, exclusions and readable trees. | Generated Windows/Linux cases cover supported paths, links, bounds, source changes and exclusive outputs. Read the module's validation record for skips and scope. |
| Python / HTTP backend | [Resource Monitor](../tools/resource-monitor/README.md): aggregate sampling, monotonic rate calculations, bounded history, loopback HTTP routes and per-session API capability checks. | Generated provider tests, actual HTTP requests and explicitly recorded live sampling are separate checks. The held historical monitor is not part of this implementation. |
| JavaScript / browser client | [Resource Monitor client](../tools/resource-monitor/README.md): module-based rendering, asynchronous polling, unavailable/error states, pause/resume viewing and explicit downloads. | Pure presentation tests use Node 24; browser interaction is recorded separately. No dependency implementation is presented as original frontend work. |
| HTML / CSS | [Resource Monitor dashboard](../tools/resource-monitor/README.md): local assets, semantic controls, responsive layout and first-party styling. | Inspect the demo without collecting real machine metrics. Browser checks cover the recorded view and interactions, not every browser/accessibility configuration. |
| C# / .NET | [Hash Journal](../tools/hash-journal/README.md): strict bounded JSONL parsing, SHA-256 chaining, optional expected-head checks and fresh-only snapshot writes. | The dependency-free console harness tests original fixtures and malformed inputs on Windows/Ubuntu. Hashes are not signatures; anchors must come from a separate trusted record. |
| JavaScript / Node.js / SQL | [Local Site Builder](../tools/local-site-builder/README.md): local HTTP application, SQLite-backed content, image handling, publishing and backup/export paths. | Existing application CI and documented fictional walkthroughs. Generated sites, databases and customer content stay private. |
| Python / SQL | [Job & Quote Tracker](../tools/job-quote-tracker/README.md): SQLite records, revisions, constraints, explicit decisions and recovery. | Existing fixture and Tk checks. Operator-entered records do not independently prove approval authority. |
| Java / Swing | [File Audit](https://github.com/TheOutlandsDev/outlands-game-tools/tree/main/tools/file-audit): selected-folder inventory, hashes and duplicate candidates through desktop and CLI entry points. | Published separately in the game-tools collection with Java 17/21 test evidence; the application itself is a general file utility. |
| Python / Windows API | [App Affinity Launcher](../tools/app-affinity-launcher/README.md): explicit process creation, pre-resume affinity/priority readback and owned-child cleanup. | Nine actual Windows disposable-process tests complement portable lifecycle cases; no universal game-compatibility or performance claim. |

## Archive and compiled-metadata mechanisms

| Language | Concrete implementation | Review limits |
| --- | --- | --- |
| PowerShell / .NET ZIP APIs | [ZIP Package Policy Verifier](../tools/zip-package-policy/README.md): strict policy parsing, bounded archive snapshots, safe member names and bounded literal text checks. | Generated archive/policy cases run with PowerShell 7 on Windows and Ubuntu. This is policy inspection, not a malware scanner or authenticity signature. |
| C# / ECMA metadata | [.NET Public API Diff](../tools/dotnet-api-diff/README.md): typed metadata signatures, visible declaration matching and deterministic differences without code loading. | Authored fixture assemblies test the documented declaration subset on Windows and Ubuntu; trusted builds only, with no full compatibility claim. |
| Python / binary text scanning | [Offline ELF Inspector](../tools/offline-elf-inspector/README.md): optional bounded runtime-reference text hints, explicit coverage and separate declared dependency evidence. | Generated ELF cases exercise hint limits and graph separation. String presence is not proof of runtime behavior. |

## Saved text, project references and inventory rules

| Language or layer | Concrete implementation | Evidence boundary |
| --- | --- | --- |
| PowerShell / text parsing | [FFmpeg Capture Log Inspector](../tools/ffmpeg-log-inspector/README.md): bounded offline progress parsing, explicit format coverage and separate diagnostic markers. | Original saved-log fixtures on Windows/Ubuntu; no live capture, FFmpeg execution or media-quality verdict. |
| Python / structured project data | [VPD Media Reference Checker](../tools/vpd-reference-checker/README.md): strict bounded JSON traversal, typed reference roles and opt-in local metadata mappings. | Generated supported-subset projects and filesystem fixtures; no editor execution, media-content reading or universal VPD compatibility claim. |
| Python / report contracts | [Source Inventory classifier](../tools/source-inventory/README.md): strict rules, pinned CSV/summary checks, deterministic matching and explicit overlap/unmatched reports. | Generated inventory/rule cases preserve the original inventory behavior. Categories do not establish licenses or permission to publish. |

## Repository metadata and document asset inspection

| Language or layer | Concrete implementation | Evidence boundary |
| --- | --- | --- |
| Python / Git subprocesses | [Git worktree reporter](../tools/git-worktree-reporter/README.md): explicit executable selection, bounded subprocesses, porcelain parsing and isolated configuration policy. | Disposable repository fixtures; no network synchronization, backup guarantee or arbitrary-repository sandbox claim. |
| Python / PDF geometry | [PDF text bounds](../tools/pdf-text-bounds/README.md): isolated parser worker, selected page-box geometry, finite tolerances and bounded reports without extracted text. | Generated real-PDF parser fixtures and separate visual QA; geometry is narrower than complete rendering quality. |
| Python / XML and CSS observations | [SVG inspector](../tools/svg-content-inspector/README.md): bounded updated XML parsing, reference indexing and explicit unsupported/uncertain syntax coverage. | Authored static fixtures; no rendering, external resource access, sanitization or universal safety verdict. |

## Configuration parsing and offline change review

| Language or layer | Concrete implementation | Evidence boundary |
| --- | --- | --- |
| Python / Android init text | [Init service index](../tools/android-init-inspector/README.md): literal section parsing, bounded declaration/reference matching and explicit unresolved coverage. | Authored temporary rc files; no init execution, properties/import resolution or boot proof. |
| Python / Make declarations | [Copy-map inspector](../tools/android-copy-map-inspector/README.md): bounded line folding, strict root JSON and declared path-conflict classification. | Fictional declarations; no Make evaluation, payload copying or effective build inference. |
| Python / Linux and Android fstab | [Fstab diff](../tools/fstab-diff/README.md): explicit field modes, ambiguous duplicate matching and relative common-target order. | Generated text comparisons; no filesystem probing, mount or device validation. |

## Bounded binary metadata, graph analysis and XML declarations

| Layer | Concrete implementation | Evidence boundary |
| --- | --- | --- |
| Python / binary metadata | [GPT inspector](../tools/gpt-image-inspector/README.md): bounded stable random reads, structured fields, CRC32 and range/agreement checks. | Generated regular image files; no physical-drive access, full payload integrity or bootability claim. |
| Python / graph algorithms | [Module inspector](../tools/kernel-module-inspector/README.md): literal text parsing, ambiguous name resolution, iterative cycle witnesses and selected topological ordering. | Supplied snapshot metadata; no real module loading, native alias resolution or kernel ABI proof. |
| Python / XML declarations | [VINTF inspector](../tools/vintf-manifest-inspector/README.md): original bounded restricted XML reading and identity-aware HAL comparison without arbitrary duplicate pairing. | Authored XML; no effective fragment merge, full schema/compatibility-matrix validation or running-service proof. |

## Review without private data

Start with the module's fictional demo, documented build/runtime and fixture
commands. The repository's workflows show the exact OS/runtime matrix. Read the
scope and provenance records before importing real inputs or interpreting a pass.
Keep stores, histories, inventories, metrics, journal events and launch receipts
in an external private workspace. Public examples are original generated data.

## Suggestions

Use the [tool-specific issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)
to propose useful behavior, report a minimal fictional reproduction or discuss a
limitation. Contributions should add tested functionality and clear maintenance
value; language counts and framework counts are not acceptance criteria.
