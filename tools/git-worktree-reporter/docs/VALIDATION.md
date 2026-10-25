# Validation record - 2026-10-25

Local CPython 3.12.7 / Windows / Git 2.53: **51 unittest methods discovered,
50 passed and one native-symlink privilege case skipped**, with warnings treated
as errors. The native symlink case is required on Linux; the Windows skip is not
a pass. Current Windows/Ubuntu CPython 3.12/3.13 outcomes are recorded by the
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
