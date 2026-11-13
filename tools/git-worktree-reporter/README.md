# Git Worktree Review Reporter

Record supported staged, unstaged, untracked and unmerged entries; branch/HEAD state; and available upstream ahead/behind counts from stored local refs. The inspector runs read-only Git commands against an explicitly selected trusted local repository. It does not fetch, push, stage, commit, check out, back up or restore your work.

Download the [0.1.0 standalone source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/git-worktree-reporter-v0.1.0), verify SHA256SUMS and follow the [complete fictional walkthrough](USAGE.md). Supply ordinary CPython 3.12–3.15 and a separately installed trusted Git 2.49+ executable. Qualification pins Git 2.56.1 and Python 3.15.2 for that minor; actual versions, native skips, source/ZIP hashes and Git archive/source/binary pins belong to release VALIDATION.json. No interpreter, Git binary or third-party Python package is bundled.

## Explicit trusted inputs

Pass absolute paths to the real Git executable, exact worktree root and a new external report directory:

```text
python -I -B git_worktree_report.py --repo ABS_WORKTREE_ROOT --git-executable ABS_TRUSTED_GIT --output ABS_NEW_REPORT
```

The runtime does not discover Git from PATH. Windows requires an ordinary `.exe`. Ordinary repositories and supported linked worktrees are accepted; bare repositories, root subdirectories, linked/reparse path components and UNC/device paths are unsupported. Use trusted stable local files and repository configuration with one operator. The safeguards do not make an arbitrary executable or hostile repository safe.

Global/system config and inherited Git/SSH/helper variables are isolated. Protected settings disable optional locks, FSMonitor, hooks, external diffs, lazy fetching and protocols. Local filters, includes, partial-clone, shallow/graft/alternate, sparse and custom-worktree layouts are refused. Local Git LFS filter configuration is refused; disabled global filter drivers and LFS object preservation are not validated. Isolating global ignore, attributes, EOL and other settings can change status from your normal interactive Git.

Git can read tracked file bodies internally when calculating status. Reports contain no source excerpts or remote URLs, but private JSON includes relative filenames, branches/refs and object IDs. Those can identify projects or people. Neither the report nor omission of absolute paths is anonymization or publication clearance.

## Fresh reports

A successful run returns exit 0 and a complete stdout summary, including for dirty work. It exclusively creates `report.json` and `MANIFEST.json` below the new report directory. The manifest records report byte length and SHA-256. The parent must already exist; output inside the selected worktree or linked/common Git metadata is refused, including tested Windows short/long aliases. Existing files and directories are never replaced.

Handled input/configuration/format/limit/change/output failure returns exit 2 with `INCOMPLETE` and a fixed error code. Raw Git stderr and selected paths are omitted from handled error JSON. I/O failure can leave a new partial output; it is not a complete report. Retain it privately and use another new destination for a retry. No cleanup, rollback or overwrite feature is provided.

Ahead/behind uses stored local refs without network refresh; unavailable comparisons remain null. Ignored files and submodule contents are excluded. An untracked nested repository can produce a directory record such as `? nested/`, outside the preserved portable path subset. That case returns exit 2 with `INCOMPLETE` / `STATUS_PATH_UNSUPPORTED` and creates no report; it is not a partial successful inventory. Staged and unstaged counts may overlap, while conflicts have a separate unmerged count. A report does not prove that work is committed, pushed, backed up, recoverable, secret-free or eligible for licensing.

## Optional pinned Git preparation

You can use an already approved trusted Git 2.49+ executable. The separate [preparation recipe](packaging/prepare_git.py) recreates the qualification dependency in a new external directory and records its hashes:

```text
python -I -B packaging/prepare_git.py --out ABS_NEW_EXTERNAL_GIT --report ABS_NEW_EXTERNAL_JSON
```

Preparation downloads hash-pinned official material and writes only its selected new preparation/report paths. It is separate from the inspector and the eleven-case guide. Windows prepares portable MinGit. Ubuntu requires an existing compiler, make and zlib development headers, plus a space-free prefix; the qualification build disables CURL, EXPAT, GETTEXT, TCLTK, PERL and PYTHON support. It does not install missing prerequisites or change system Git/PATH. Follow applicable tool/network policy; the inspector also accepts other approved trusted Git installations meeting its minimum.

## Fictional fixtures and qualification

The [guide](USAGE.md) checks the raw demo generator and dirty, clean, linked, detached and unborn inspections, then exercises five expected refusals. The demo generator deliberately initializes and commits a new disposable repository; fixture Git commands are separate from the inspector's read-only behavior. No existing project is copied or inspected.

The [current qualification contract](docs/QUALIFICATION.md) preserves all 54 original tests and adds 30 copied-runtime methods per lane on Windows and Ubuntu with Python 3.12–3.15. The preserved [format contract](docs/FORMAT.md) and [earlier validation record](docs/VALIDATION.md) retain historical Python 3.12–3.14 wording and earlier results; the release validation record describes this qualification. See [provenance](docs/PROVENANCE.md), [private workspace guidance](docs/PRIVATE-WORKSPACE.md), [changes](CHANGELOG.md), [contributing](CONTRIBUTING.md) and [license](LICENSE).

Observed control hashes and bounded owned children detect tested changes/failures. They do not provide an atomic snapshot, complete loose-ref/object/worktree locking, hostile-process sandbox, hard native I/O/startup deadline or universal filesystem/configuration support. Network/cloud storage, malicious mutation and real migration recovery are outside acceptance. Use workplace-approved tools and permissions; this guide requests no administrator privilege or policy changes.
