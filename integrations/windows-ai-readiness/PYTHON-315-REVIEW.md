# Python 3.15 source compatibility review

Checked on Windows 11 with Python 3.15.2 on 2026-11-09. This is a separate
compatibility exercise. The 76 released independent wheels, nineteen group
wheels, and selector still all declare `Requires-Python: >=3.12,<3.14`.
Their supported install and CI lanes remain Python 3.12/3.13.

All 1,595 Python source/test files under `tools/` parsed with the Python 3.15
AST parser without syntax errors. The 222 catalog tool directories were then
run as separate test roots to avoid collisions between repeated module names.
The first isolated pass had 179 passing tool suites, eight failing suites,
and 35 directories without `tests/test_*.py` files. After installing the
declared or current PDF/document dependencies and rerunning three affected
suites, 182 tool suites passed, five still failed, and 35 had no matching test
suite. Passing suites can contain explicit skips; these counts are by tool
directory, not individual test method.

| Remaining tool | Observed boundary |
| --- | --- |
| `app-affinity-launcher` | Four native process/affinity tests failed, including a process ID mismatch. |
| `dependency-lock-tools` | Six tests failed; symlink creation returned Windows privilege error 1314 in the sandbox. |
| `resource-monitor` | Two launcher tests failed because its supported-runtime guard rejects Python 3.15. |
| `safe-file-mover` | 57 native filesystem tests failed, including named-stream cases; this environment cannot establish its Windows behavior. |
| `xml-recipe-inspector` | Four tests failed, including symlink creation blocked by Windows privilege error 1314. |

`document-builders` passed 64 tests with eight skips after its dependencies
were installed. `portfolio-builder` passed 41 with one skip after installing
`pypdf`. `pdf-text-bounds` passed 54 with two skips using its declared
development pins, including `pypdfium2==5.14.0` and `pypdf==6.21.2`.
With newer `pypdfium2==5.15.2` and `pypdf==7.0.0`, that suite had 38
failures, so its exact dependency pins matter. The newer dependency set was
not substituted into the released tool.

This review establishes Python 3.15 syntax and isolated test observations;
it does not certify the 76 wheel installs on 3.15, all Windows native features,
or every newer library version. Do not use `--ignore-requires-python` to turn
an unsupported wheel into a claimed supported installation.
