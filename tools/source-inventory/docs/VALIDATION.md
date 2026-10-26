# Validation record — folder-tree enhancement

## Current Windows filesystem hardening

The original 92 inventory/tree/classifier methods remain byte-identical.
Local Windows/Python 3.12.7: 85 passed/seven skipped. New 32 safety methods:
22 passed/ten skipped, no failures/errors. Nine native link/junction cases
are unavailable in this sandbox; one is Linux-only. Short-name rejection ran.
CI requires Windows link/junction cases; optional short-name absence is explicit.

A copied three-file runtime passed 28 fresh processes (25 direct CLI, three
controlled failures), with fictional report/tree/manifest/parser and classifier
checks. Input/runtime bytes remained unchanged, no bytecode appeared, and all
reports/captures remain private. Late failure deliberately retains an
unconfirmed complete-looking summary. See [the Windows contract](WINDOWS.md).

## Historical extension results

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

## Rule classification extension — 2026-10-25

Local Windows / Python 3.12.7: **92 unittest methods discovered, 85 passed,
seven skipped**, with no failures, errors or warnings. The run used
`python -B -W error -m unittest discover -s tests -v`, so the earlier invalid
test-literal escape warning was corrected rather than ignored. The original
39 inventory/tree methods remain; 53 new methods exercise classification and
its generated example. The existing five Windows skips remain, plus a new
POSIX FIFO case and a new native-symlink privilege case. Native skips are not
passes. Linux CI runs the applicable FIFO and link cases; check the linked
Actions results for the supported OS/Python matrix.

The new fixtures cover ordered first-match selection with all matching IDs,
overlap reporting, shared-category byte totals without double counting,
unmatched/empty reports, case sensitivity and Unicode case-folding, exact/
prefix/suffix literal behavior, deterministic sorting, strict rule fields and
types, duplicate fields/IDs, no regex/glob dispatch, unsupported paths, safe
labels, NaN/fraction rejection, malformed/oversized/deep JSON and surrogate
text/keys, exact CSV headers/column counts, duplicate rows, file statuses and
digests, invalid UTF-8, source summary/hash/count/top-level consistency, canonical
apostrophe/formula-path decoding and re-encoding, no body rescanning, work/count/
report limits, nonregular/link rejection where available, detected input changes,
fresh/exclusive outputs, partial-output errors, independent output manifest
hashes, safe CLI errors/counts, and unchanged input bytes.

The fictional CLI generator was also exercised separately: four selected rows,
three selected categories, one unmatched file and one overlapping file. The
classifier reused the generated report and did not import or execute fictional
source text. It does not execute or depend on the archived device-inventory
helper. No original device/project inventory or real source tree was inspected
by this extension's tests.

These checks establish the documented supplied-report behavior. They do not
authenticate the report, establish file licenses, inspect original body hashes,
prove complete source coverage or guarantee behavior on an adversarial/live
filesystem. Optional tree metadata is not validated by classification. The
paired CSV/summary hash can be rewritten together, and user categories have no
independent technical/legal authority.
