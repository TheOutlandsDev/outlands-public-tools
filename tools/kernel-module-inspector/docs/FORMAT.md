# Literal module metadata grammar

Text inputs: strict UTF-8 (optional BOM), LF/CRLF, at most 1 MiB each, 4 MiB total,
20,000 physical lines including the final empty line, 8,192 characters per line.
Blank/full-line `#` comments are ignored. ASCII spaces/tabs delimit dependency
tokens. No inline comments, quoting, continuation, expansion or escaping.

Dependency rows have exactly one colon: `relative/module.ko: relative/other.ko`.
Empty dependency lists are allowed. Module suffixes .ko, .ko.gz, .ko.xz and .ko.zst
are supported as literal text, not decompressed. Paths use forward slashes with
ASCII letter/digit/dot/underscore/hyphen components, at most 512 characters,
excluding empty/dot/parent components. Other syntax is incomplete coverage.

Load-list rows are one supported path/name each. Exact metadata paths take
precedence, otherwise a unique literal basename or basename without its module
suffix can match. No aliases, builtin list, environment, modprobe configuration,
dash/underscore conversion or installed module search is performed. Duplicate
metadata keys are excluded from unique resolution; repeated load selections
are findings. Dependency references require exact paths in the selected metadata.

Optional available inventory is one full supported relative module path per
line. It records caller-declared membership only; no file is opened through a
declared module name. Missing entries are not proof of missing real binaries.
Dependencies absent from the load list alone are not flagged as missing.

Maximums: 2,000 accepted declarations, 4,000 dependency tokens (including
duplicates before normalization), 8,000 total IDs in cycle witnesses and common
4,000-row report collections. Deep graphs use iterative traversal. Actual DFS
back edges produce closed cycle witnesses; nodes merely blocked by a cycle are
not misidentified as cycle members. Witnesses are not an enumeration of every
possible cycle.

Kahn ordering is dependency-first over unique declared nodes. Unknown/ambiguous
prerequisites and their dependants stay blocked. Selected output is restricted
to resolved load roots and their known declared dependency closure. Unrelated
findings still make the overall report require review. The boolean
selected_plan_complete_within_metadata concerns only this supported selected
closure; it does not verify inventory membership, ABI, kernel compatibility or
successful loading. No script/load command is produced.

Schema version 1 includes modules, dependencies, load_entries, cycle_witnesses,
selected_dependency_order, blocked_selected_modules, selected plan completeness,
declared_inventory_checked, inputs, findings, coverage_issues and status.
Default paths/names are omitted. IDs depend on declaration order, not persistent
identity. Details opt-in adds declared paths and selected names.
