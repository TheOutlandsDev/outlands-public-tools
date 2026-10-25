# Validation record — App Affinity Launcher 0.1.0

## Scope and evidence

Local Windows / Python 3.12.7: **74 tests discovered, 71 passed, three skipped**,
with no failures or errors. All **nine native Windows tests passed**, including
the public disposable example. Two symlink cases require permissions this
account lacks; the remaining skip applies only to Linux. Skips are not passes.

The standard-library suite separates portable policy/lifecycle checks from real
Windows process tests. Portable cases use fake backends and generated paths and
arguments; they do not establish Windows API behavior. Native cases use generated
disposable Python children and inspect their own startup mask, priority, working
directory and literal arguments. No game is required by these cases.

The dedicated CI workflow runs Windows/Ubuntu with Python 3.12/3.13. Native
Windows cases are explicitly skipped on Ubuntu; skips are not counted as native
passes. Test totals, platform outcomes and any limitations are recorded in the
[Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions).

Checks cover the cases present in the source suite: affinity/argument bounds,
planning versus launch, duplicate handling, native call ordering, setup-failure
cleanup, pre-resume readback, optional wait behavior and disposable child
observations. Review individual tests before extending these claims to new
architectures, processor groups or applications.

Source inventory/hash/UTF-8 checks and local documentation links are reviewed
separately. An inventory records selected bytes; it does not prove exclusive
authorship, universal license clearance, absence of every secret or application
correctness.

## Limits of acceptance

Single-processor-group Windows support is the initial scope. Multi-group
machines, every Windows security policy, elevated targets, cross-user duplicate
visibility and arbitrary custom argument parsers are not established by these
fixtures. The tool does not elevate or silently drop unsupported CPU selections.

A successful setup receipt establishes the recorded mask/priority before the
primary thread was resumed. It does not prove that an application subsequently
initialized, retained that mask, used every selected processor, avoided creating
other processes or performed better. Specific applications and games require
separate usable-startup/stability validation; no such compatibility claim is
made from the historical wrapper or these tests.

For a new application acceptance run, record source commit, Windows/Python,
processor-group support, allowed/selected masks and redacted receipt. Exercise
normal startup, working directory, argument handling, normal shutdown and a
representative workload. Keep actual paths, arguments and operational outputs
private. Use the application's own supported controls to close it.
