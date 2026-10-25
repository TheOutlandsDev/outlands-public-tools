# Validation record - 2026-10-25

Local CPython 3.12.7 / Windows / Git 2.53: **54 unittest methods discovered,
52 passed and two native Windows cases skipped**, with warnings treated as errors.
The skips are unavailable symlink privilege and unavailable 8.3 aliases on the
selected private fixture volume. The alias regression runs when native aliases
are available; a portable simulated-alias containment case also runs everywhere.
The native symlink case is required on Linux. Skips are not passes.
Current Ubuntu CPython 3.12/3.13 and Windows CPython 3.13/3.14 outcomes are recorded by the
[repository checks](https://github.com/TheOutlandsDev/outlands-public-tools/actions).

The suite uses only newly generated disposable repositories. It covers actual
ordinary and linked worktrees, unborn/detached heads, local upstream ahead/behind,
staged/unstaged/untracked entries, staged renames with spaces, ignored-file scope,
exact-root enforcement, supported metadata refusal, unchanged HEAD/index/control
bytes, fresh reports and independent manifest readback. Generated porcelain adds
UTF-8 space/tab/newline paths, copied/renamed pairs, unmerged records, SHA-256 IDs,
unknown optional headers, unavailable upstream counts, malformed/truncated records,
duplicates, wrong modes/statuses/counts, path/entry/output limits and encoding errors.

Poisoned filter configuration is refused before status; configured FSMonitor and
post-index-change hook sentinels remain unexecuted. Includes, partial-clone,
shallow/graft/alternate, sparse/custom-diff and custom-worktree cases fail closed.
Inherited/global Git-variable injection is isolated. Authored child-process cases
exercise stdout/stderr bounds, nonzero private errors and timeout cleanup. These
are tests of owned trusted child execution, not arbitrary hostile-process evasion.

One initial rename fixture had replaced the entire file before renaming it, so
Git correctly reported delete/add rather than a rename. The fixture was corrected
to preserve the baseline content for the intended 100% rename case; no status
check was weakened. Unmerged entries are counted separately, not mislabeled as
normal staged or unstaged changes. The final run follows these corrections.

No real project was inspected, fetched, pushed, copied or restored for acceptance.
No remote server, credentials, repository source or private reports entered the
public source tree. Test generators create commits only in their newly owned
fixture repositories; the runtime inspector contains no commit operation.

These checks do not establish every Git configuration/filesystem/encoding,
malicious repository safety, an atomic snapshot, complete ignored/submodule
coverage, LFS preservation, remote freshness or full migration recovery.

Hosted Windows testing exposed a short/long-name alias overlap: Git returned a
canonical common-directory path while the requested output retained a DOS alias.
Lexical containment could then miss the same physical metadata directory. Existing
directories are now checked for links before canonicalization, expanded to their
physical spelling, checked again, and compared before any output is created.
The original failing linked-worktree test remains intact; alias and validation-order
regressions accompany it. This is a focused containment correction, not a weakened check.

A separate native Windows acceptance probe used a newly generated fictional
repository and linked worktree on an 8.3-enabled temporary volume. Distinct short
and long common-directory paths were verified to identify the same directory;
the inspector refused the aliased output with `OUTPUT_INSIDE_GIT_METADATA` before
creating it. That probe passed. The local unittest volume's alias-unavailable
skip remains reported separately, rather than counted as native acceptance.
