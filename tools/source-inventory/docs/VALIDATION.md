# Validation record — folder-tree enhancement

The earlier Source Inventory edition recorded 18 Linux synthetic methods. This
edition retains those methods and adds generated tree-export cases. Windows
fixtures account for filesystem filename restrictions, case behavior, inherited
permissions and symlink creation privileges; original POSIX coverage remains.

The suite checks default two-report compatibility, exact hashes/order, source
change and read failures, private/exclusive outputs, source/output boundaries,
entry/file/byte limits, selected tree scope, empty directories, additive
exclusions, deterministic rendering, escaped control/bidi names, depth omissions,
exact tree hash and the 1 MiB tree bound. A created-then-written file exercises
the Windows path/fd stat identity issue without changing real source files.

Local Windows / Python 3.12.7: **39 methods discovered, 34 passed, five skipped**,
with no failures or errors. Two skipped methods require POSIX filename/FIFO
semantics. Three require Windows symlink creation permission this account lacks.
CI outcomes for Windows/Ubuntu Python 3.12/3.13 are recorded in the
[Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions).
Skips are not passes.

Fixture runs use bounded temporary directories only, with network calls denied
by the retained test harness. A fictional example generator is separately
exercised against the CLI. No live project tree, game, secret store or original
export helper is run. Text reports retain relative names and metadata and must
be reviewed before public sharing.

File mutation, growth/replacement, traversal failures and output failures must
remain failures. Tree depth is an explicitly incomplete display, reported in
summary metadata; it does not silently alter inventory coverage. A report
manifest/hash identifies selected bytes, not ownership, every possible secret,
or the state of an entire filesystem at one moment. Trusted quiescent parents
and inputs remain necessary.
