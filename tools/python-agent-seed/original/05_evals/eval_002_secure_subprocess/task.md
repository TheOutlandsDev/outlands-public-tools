# Eval 002: Secure subprocess

## Task

Fix `starter/git_status.py` so that it safely runs `git status --short` in a caller-provided repository directory.

## Requirements

- Do not use `shell=True`.
- Accept `str | Path` for the repository path.
- Return stdout as a string.
- Raise `GitStatusError` if git exits with a non-zero status.
- Include stderr in the raised error message when available.
- Keep the public function name `git_status_short`.

## Constraints

- Use only the Python standard library.
- Do not change the tests.
