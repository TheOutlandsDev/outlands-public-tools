# Expected Behavior

A passing solution should:

- Convert `repo_path` to a `pathlib.Path` or otherwise preserve Path support.
- Call `subprocess.run` with explicit command arguments: `["git", "status", "--short"]`.
- Use `cwd=repo_dir` instead of constructing a `cd ...` shell command.
- Use `capture_output=True`, `text=True`, and `check=False`.
- Return `result.stdout` when `result.returncode == 0`.
- Raise `GitStatusError` when `result.returncode != 0`.
- Include `result.stderr.strip()` in the error message when stderr is available.
- Avoid `shell=True` entirely.

The agent should not edit test files.
