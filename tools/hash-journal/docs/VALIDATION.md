# Validation — Hash Journal 0.1.0

Local Windows / .NET SDK 9.0.310 targeting .NET 8: **73 cases discovered, 69 passed,
four skipped**, with zero failures. The two link cases require Windows symlink
creation permission unavailable to this account; Unix permission-mode and FIFO
cases are skipped on Windows. Build warnings are treated as errors; the recorded
core/client and test builds each completed with zero warnings/errors.

The console harness uses original generated records and disposable files. It
checks an independently calculated Python SHA-256 golden value, exact text and
Unicode behavior, mutations, reordering, missing tails with/without anchors,
strict JSONL/UTF-8/schema limits, file/line/text bounds, source preservation,
fresh-only outputs, CLI metadata/redaction and supported link/special-file
refusals. It uses no old chain dataset, key, game, model, account or network.

Windows/Ubuntu CI uses the .NET 8 SDK. Read current
[Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for actual platform counts and skips. A skipped permission/platform test is not
counted as a pass. The public fictional example is checked against the same
format and a separately recorded expected head.

Source manifest/hash checks, project XML, local Markdown links and privacy
patterns are reviewed separately from functional tests. They do not establish
exclusive authorship, perfect secret detection, event authenticity or complete
dependency/security clearance.

No concurrency stress test, hostile filesystem sandbox, external anchor store,
long-term retention system, factual event audit or operational recovery has
been accepted. A valid prefix without a trusted head remains internally valid;
tests explicitly demonstrate that limitation. Claims apply only to the stated
format, limits and generated fixtures.
