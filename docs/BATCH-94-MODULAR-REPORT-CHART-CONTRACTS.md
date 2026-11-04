# Batch 94: offline report and chart contracts

Four independent MIT source tools check supplied report parameters, dataset field aliases, chart encoding declarations, and chart point coverage. Each has its own CLI and fictional example. Shared checked-file helpers are copied from already public MIT source; no original private implementation or dataset is included.

The parameter checker validates types, defaults, choices, ranges, and conditional activation for selected cases. The dataset binding checker compares declared report fields with a pinned dataset schema. The chart encoding checker compares mark and axis declarations with a pinned field schema, using exact opaque unit labels. The coverage reconciler compares ordered point identities and series assignments with a pinned row snapshot, preserving missing, extra, repeated, and reordered claims.

These checks consume caller supplied declarations only. They do not execute SQL, open a database, render a chart, inspect source values, or prove source completeness. Reports and identifiers derived from real inputs may be private. The tools remain source-only; combined packaging is deferred.
