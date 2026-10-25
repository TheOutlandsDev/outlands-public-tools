# Git Worktree Review Reporter

Record local Git status before migrating, archiving or reviewing your own coding
work. This Python command reports supported staged, unstaged, untracked and
unmerged entries; current branch/HEAD state; and available upstream ahead/behind
counts from stored local refs. It handles ordinary repositories and supported
linked worktrees, without fetching, pushing, staging, committing or checking out
anything. Only explicitly selected trusted local repositories are supported.

The implementation is original [MIT source](LICENSE), generalized from the
owner's local source-preservation helpers. No private repository, source content,
remote URL or preservation receipt is included. Dependencies and inputs retain
their own rights. See [provenance](docs/PROVENANCE.md).

## Requirements and trust boundary

- CPython **3.12 or 3.13** and a separately installed, trusted **Git 2.49+**.
- Explicit absolute paths to the real Git executable and exact worktree root.
  Git discovery happens only in the test harness, never in the runtime inspector.
- A stable, ordinary local filesystem and trusted repository/configuration.
  Existing symlinks/reparse points in input path components are refused.
  UNC/device paths, filesystem roots and a repository subdirectory are unsupported.
- No active build, editor or Git process changing the selected worktree while
  inspecting it. This is not an atomic snapshot or an adversarial-filesystem
  sandbox. OS file opens and native process startup do not have a hard timeout.

Git is an executable with its own parser, configuration and filesystem behavior.
The tool isolates global/system configuration and inherited Git variables, refuses
configured filters/includes/partial-clone and other unsupported layouts, and
disables optional locks, FSMonitor, hooks, external diff helpers, protocols and
lazy fetching. These safeguards are tested; they do not make an untrusted Git
binary or arbitrary hostile repository safe. Git can read tracked file bodies
internally when computing status; the report contains no excerpts or file bodies.

Configured local/worktree filter drivers, including local Git LFS drivers, are refused.
Global/system drivers are disabled rather than inventoried. A repository relying
on a global LFS/clean driver can therefore have different isolated status; LFS
objects, driver requirements and preservation are not validated.
Shallow history, grafts, alternate object stores, sparse configuration and custom
worktree redirection are refused rather than producing an incomplete graph claim.
See the complete [supported subset and safeguards](docs/FORMAT.md).

## Run a fictional example first

Clone or download [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and open a terminal in `tools/git-worktree-reporter`. No Python packages are needed.
Use an existing [external private workspace](../../docs/PRIVATE-WORKSPACE.md).
Replace `ABS_GIT` with the absolute path to your trusted real Git binary, and
`ABS_NEW_DEMO` / `ABS_NEW_REPORT` with new absolute directories outside the checkout.

```text
python -B examples/make_demo.py --git-executable ABS_GIT --destination ABS_NEW_DEMO
python -B git_worktree_report.py --repo ABS_NEW_DEMO --git-executable ABS_GIT --output ABS_NEW_REPORT
```

The example generator deliberately creates and commits an authored baseline in
its new disposable repository. It leaves one staged change, one unstaged change
and one untracked file. It never copies your existing source. The inspector itself
performs no commit or repository-writing operation. The expected CLI summary is:

```json
{"counts":{"staged":1,"unmerged":0,"unstaged":1,"untracked":1},"entry_count":3,"head_state":"branch","status":"LOCAL_STATUS_RECORDED"}
```

Whitespace/key order may differ. The new report directory contains:

- `report.json`: branch/status observations, relative names, limits and coverage.
- `MANIFEST.json`: the report's exact byte length and SHA-256.

Outputs use exclusive creation and do not overwrite an existing file/directory.
The parent must exist. Outputs inside the selected worktree or linked/common Git
metadata directory are refused. An I/O error can leave a new partial output;
the command returns failure and does not claim a complete report.

## Review your own worktree

```text
python -B git_worktree_report.py --repo ABS_WORKTREE_ROOT --git-executable ABS_GIT --output ABS_NEW_REPORT
```

| Exit | Meaning |
| --- | --- |
| `0` | Supported local status recorded; help also exits zero. Dirty work is not an error. |
| `2` | Input, configuration, format, limit, observed-source-change or output failure; inspection is incomplete. |

Stdout prints counts and HEAD state, not source paths, branch names or Git errors.
The private JSON includes **relative filenames, branch/ref names and object IDs**.
Those can identify projects, people and work. Review before sharing. Omission of
absolute paths is not anonymization or a guarantee that a filename contains no
sensitive text. Raw Git stderr, remote URLs and source content are not emitted.

## Interpret the result carefully

- `staged` and `unstaged` counts can overlap for one changed file; unmerged entries
  have a separate count and are not described as ready staged changes.
- Ignored files and submodule contents are outside the inspection. Untracked
  nested repositories can appear as directory entries rather than a complete
  enumeration of the nested repository. This is not a file-content inventory.
- Ahead/behind counts use stored local refs. Remote-tracking refs may be stale;
  there is no network refresh. An unavailable upstream comparison is `null`, not
  zero. The report does not establish that all work is committed, backed up,
  pushed, recoverable, secret-free or eligible for public licensing.
- Global/system config is deliberately disabled. User-wide ignore, attributes,
  EOL and other settings can therefore differ from an ordinary interactive status.
  The report describes this isolated supported configuration, not every user setup.
- Git status can be expensive. Each owned child has output/time bounds, and
  observed control files are compared before/after. Worktree file changes or loose
  ref races are not a complete transactionally consistent snapshot.

## Tests and suggestions

```text
python -B -W error -m unittest discover -s tests -v
```

The harness discovers Git only for tests, or uses the explicit `OUTLANDS_TEST_GIT`
environment variable. Git is required; tests are not skipped when it is absent.
All repositories are newly generated in temporary private directories. Read
[validation](docs/VALIDATION.md), [format details](docs/FORMAT.md) and the
[fictional walkthrough](examples/README.md).

Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=git_worktree_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=git_worktree_suggestion.yml).
Include OS, Git/Python versions, source commit, safe error code and a minimal
fictional reproduction. Do not upload real repositories, `.git` directories,
unredacted status reports, credentials or proprietary source. Contributions and
supported-layout suggestions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
