# Contributing

Use small fictional cases and the exact source revision when describing an
issue. Never attach a real database, journal, export, recovery copy, target,
finding, authorization document, credential or private project. Neutral-looking
IDs and status codes can still identify an assessment.

Before proposing a change, run the source check and fictional suite described
in [VALIDATION](docs/VALIDATION.md). Desktop changes need real Tk tests; parser or
storage mocks alone do not prove widget behavior or SQLite transactions. Test
outputs belong outside the checkout. Keep generated stores and reports out of
commits and release assets.

Preserve exact schema checks, public-checker semantics, explicit expected store
revisions, append-only history and new-only destinations. Add no target discovery,
execution, attachment ingestion, narrative/identity fields, telemetry or hidden
state repairs. A future schema migration needs a separately reviewed recovery
and compatibility design; do not silently rewrite an existing store.

Schema-valid review drafts are intentional. Do not turn a passing record check
into verified authorization, isolation or remediation. Keep the public record
contract, storage/UI behavior, tests and documentation consistent, and describe
actual validation without counting skips as passes.

Selected original contributions use the app's [MIT license](LICENSE), attributed
to TheOutlandsDev. Preserve applicable notices and do not submit held original
application code, records or uncleared third-party material.
