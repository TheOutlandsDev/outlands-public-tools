---
inclusion: fileMatch
fileMatchPattern: ["**/*.py","**/pyproject.toml","**/requirements*.txt"]
---
Inspect pyproject.toml, lockfiles, and CI before selecting an interpreter. For this kit's examples use CPython 3.15 and python -B -m unittest discover -s tests -v. For real projects, create a project virtual environment and install the repository's declared dependencies. Use exact compatible versions established by tests. Do not bypass Requires-Python. Reproduce a reported failure before a fix and run the relevant regression afterward. Test skips and source parsing do not establish full support.
