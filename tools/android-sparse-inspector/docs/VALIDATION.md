# Validation and limits

The initial local Windows / CPython 3.12.7 run discovers **45 methods**: 27
sparse/reader/CLI methods and 18 repeated first-party safeguard methods. The
reviewed local run passes 41 and skips four platform or unavailable link-creation
checks. Skips are not passes. A matrix run on Windows/Ubuntu checks platform
behavior separately; consult the repository's current Actions results for its
actual outcomes.

The tests generate their own small binary structures. They cover RAW, FILL,
DONT_CARE and unverified CRC declarations; empty layouts; exact block accounting;
signature/header/truncation errors; extended-header and unsupported-version/type
coverage; size equations; reserved fields; declared limits; large expanded sizes
without expansion; trailing bytes; descriptor bounds/budgets; ordinary file
mutation; actual CLI statuses; output refusal and privacy of stdout/payloads.
Common tests cover absolute regular inputs, links/reparse routes, Windows stream
syntax, POSIX FIFO refusal, text/JSON safeguards and escaped/hash-manifest reports.

Run from the module directory:

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

On a constrained local environment, point `TEMP`/`TMP` to an existing writable
private workspace before invoking tests. The tests create and clean their own
temporary directories. They never inspect your real firmware or invoke AOSP,
SDK, flash, mount or reconstruction programs.

The generated examples exercise success, explicit CRC coverage and truncated
metadata. They are not real firmware samples, an ecosystem compatibility corpus
or device tests. No payload CRC, filesystem, bootability, authenticity or
sparsechunk-set reconstruction validation is claimed. Source inventory hashes
are unsigned and do not prove exclusive authorship or universal secret absence.
