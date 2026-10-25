# Fictional worktree walkthrough

Use `make_demo.py` only with a new private destination and an explicit trusted
Git binary. It creates three authored text files and a baseline commit, then
leaves one staged, one unstaged and one untracked item. It does not copy files
from your existing repositories or install a Git binary.

```text
python -B examples/make_demo.py --destination ABS_NEW_DEMO --git-executable ABS_GIT
python -B git_worktree_report.py --repo ABS_NEW_DEMO --git-executable ABS_GIT --output ABS_NEW_REPORT
```

The inspector exits 0 with three entries. Read `report.json`: `staged.txt` is
staged, `README.md` is unstaged, and `new item.txt` is untracked. `head_state` is
`branch`; no upstream is configured, so upstream counts are unknown rather than
zero. The report's manifest records its exact bytes and SHA-256.

You may experiment only inside this generated repository, for example committing
the staged fictional change or adding a local comparison branch with your normal
Git commands, then creating a separate new report. These are deliberate fixture
changes, not automatic actions performed by the inspector. Never treat this demo
as authorization to change an existing project or publish its names/content.

Use the [main instructions](../README.md) for trust, paths and output rules.
