# Scoring Rubric

Total: 100 points.

| Criterion | Points |
|---|---:|
| Avoids `shell=True`, `subprocess.check_output`, and string shell commands | 30 |
| Uses explicit subprocess arguments and `cwd` | 20 |
| Handles non-zero status with a useful `GitStatusError` message | 20 |
| Preserves public API and returns stdout exactly | 15 |
| Uses type annotations and supports both `str` and `pathlib.Path` | 10 |
| Keeps the patch minimal | 5 |

A good solution should be safe, boring, typed, and easy to inspect.
