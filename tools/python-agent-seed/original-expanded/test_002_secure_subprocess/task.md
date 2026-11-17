# Eval 002: Secure subprocess

## Task

Fix `starter/git_status.py` so that it safely runs `git status --short` in a caller-provided repository directory.

## Requirements

- Do not use `shell=True`.
- Do not build a shell command string.
- Use an explicit argument list: `["git", "status", "--short"]`.
- Use `cwd` to select the repository directory.
- Accept `str | pathlib.Path` for the repository path.
- Return stdout as a string.
- Raise `GitStatusError` if git exits with a non-zero status.
- Include stderr in the raised error message when stderr is available.
- Keep the public function name `git_status_short`.
- Use only the Python standard library.

## Constraints

- Modify only `starter/git_status.py`.
- Do not change the tests.
- Preserve the `GitStatusError` exception class.
- Keep the patch small and easy to review.
