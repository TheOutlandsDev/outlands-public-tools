# Public origins and exclusions

Fresh generic tool code, independently written fictional formats and examples.
No private original code, business schema/mapping/formula, customer record,
endpoint, credential, deployment setting, screenshot or third-party asset was
selected. Original Z: applications were not modified, imported or executed.

The native Windows guard is copied byte-for-byte from this collection at public
revision `4faa2039e607e4dc3a9943def5bf1bae1c4bd13d`, path
`tools/environment-contract-checker/environment_windows.py`, SHA-256
`7aa8507dfcfcdba008642d53c9ba6453fd171a3e15327e7f1af7e8d8efc84537`. Its existing MIT notices are retained.
The other buffer/CLI/POSIX helper is fresh generic code, duplicated identically
across these four independent tool directories to avoid hidden sibling dependencies.
Each copy is listed in SOURCE-MANIFEST.json.

The following are byte-identical copies of the already-public planner at the
same revision, under `systems/production-planning-workbench/planning/`.
The current selection does not reopen or clear original private source.

| Public source | SHA-256 |
| --- | --- |
| `project.py` | `5fa2d1939e754dcde71507ab0d40cb9c932e56fc76ba07408e74818e6a042e44` |
| `engines/allocation.py` | `98b36f75b652f120f66e55b9a926d8c9f9a7d08558171520f73e3e63a10cc927` |
| `engines/demand.py` | `424d88ffbd037d23943aa1679e3018c81c8c4474b15efc8d648451472a3f9b5d` |
| `engines/identity.py` | `3f7b4fc6e89b8070e6ac60ea40aa7e888b5ae9d06ac70ddaed53ad33e21b88f3` |
| `engines/readiness.py` | `765e467ca7359c8aa14c8e803516155baf38c2aac33ead9908c1cb02cfcd4501` |
| `engines/__init__.py` | `a27b42accb7aa2b5e33f0650b05b1a9c76eb990b9649cc05e68997cc058c4e0e` |

The runtime shim is new, in-memory-only code. requirements.txt and the invented
project fixture are copied from the same public workbench. Third-party Pydantic
and its dependencies retain their upstream licenses and are obtained separately;
no installed wheels, binaries or dependency source are redistributed here.
The checker calls only the buffer parser and calculation path, not dormant engine
file-loading convenience functions, store code, browser handlers or CLI execution.

These tools validate structure and declarations, not anonymization or ownership.
Exact public source files and retained notices are reviewed before publication.
Generated workspaces/reports, local inventories and qualification logs stay outside
the repository. Combined packages and browser applications are deferred.
