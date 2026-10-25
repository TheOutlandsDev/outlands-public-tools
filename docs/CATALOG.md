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
