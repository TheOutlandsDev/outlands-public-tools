# Folder-tree enhancement provenance

Source Inventory's selected original source was already published under MIT in
the shared collection. The owner also retains a personal game-folder export
helper producing TXT/CSV/JSON reports with fixed paths. That helper provided
the requested use case; the new tree renderer, options, generated examples and
tests were freshly authored with AI assistance for this public enhancement.

No original fixed installation path, real inventory, project data, credential,
game content or dependency implementation is included. The retained local helper
remains unchanged; its original-path/hash record is private. No license or
attribution notice was removed. Owner-reported authorship is not independent
proof of exclusive ownership of unselected historical material.

The public boundary is an explicit-input, bounded inventory and observed-name
tree. Tree export reuses the existing selected-file collection/hash pass; it
does not perform a second broad scan. Extra basenames strengthen exclusions,
and depth limits affect display only. This is a filename/reporting utility, not
a credential detector, backup product, dependency resolver or game repair.

The selected original Python source, tests, documentation and fictional examples
are MIT licensed. Python's separately supplied interpreter/standard library
retain their own terms. There are no third-party Python package dependencies.

Windows testing exposed differing path/fd `st_ctime_ns` semantics in Python
3.12. Cross-path identity uses Windows birth time together with device, inode,
size and modification time; descriptor change time remains checked before and
after the read. POSIX retains its original change-time comparison. The fix does
not turn these observations into an atomic snapshot or hostile-writer sandbox.
