# Agent Prompt: Test 002

You are working in a Python 3.12.7 project.

Read `task.md` and modify only this file:

```text
starter/git_status.py
```

Do not change the tests.

Your goal is to safely run `git status --short` in a caller-provided repository directory.

Requirements:

- Do not use `shell=True`.
- Do not build a shell command string.
- Use an explicit argument list: `["git", "status", "--short"]`.
- Use `cwd` to select the repository directory.
- Accept `str | pathlib.Path` for the repository path.
- Return stdout as a string.
- Raise `GitStatusError` if git exits with a non-zero status.
- Include stderr in the raised error message when available.
- Keep the public function name `git_status_short`.
- Use only the Python standard library.

After editing, run:

```bash
python scripts/run_tests.py
```

Return:

1. Summary of the change.
2. Files changed.
3. Commands run.
4. Test results.
5. Any remaining assumptions or risks.
