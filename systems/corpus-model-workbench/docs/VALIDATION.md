# Fictional validation and limits

The automated suite exercises the complete app with fresh disposable stores:
deduplication/provenance, benchmark and duplicate-group holdouts, four-check
approval, FTS, separate SFT/RAG exports and independent hash checks, SQLite
backup/schema/version/sidecar refusal, JSON/gzip bounds, exclusive outputs,
workspace/source boundaries, session locks, interrupted-run recovery, fictional
model comparisons/scores/vectors/discussions, prompt caps, model error redaction,
and the real loopback HTTP UI's Host/token/Origin/error rules.

CI runs Python 3.12/3.13 on Windows and Ubuntu. Native hard-link file/store and
symbolic-link file/ancestor rejection fixtures are mandatory there using
`WORKBENCH_REQUIRE_LINKS=1`. Local runs skip these only if fixture creation is
unavailable; skips remain visible. A local Windows run discovered 61 methods:
56 passed, four native-link fixture limitations and one POSIX-only case were skipped. Native CI
results must be checked on the exact publication commit before merging.

The end-to-end demo uses two explicitly fictional model names/digests and fixed
fake answers, deterministic fake vectors and invented scores. It verifies app
orchestration and review boundaries, not model inference, quality, training or
provider compatibility. No installed service, real record, historical store or
original program instance is opened. API tests use an ephemeral loopback server. Actual local model-client tests verify proxy bypass, redirect refusal and non-finite response rejection. A real child-process termination test verifies stale-lock recovery without replay.

The UI's HTML and authenticated API responses are tested. Automated API checks
are not a full interactive browser acceptance test. Actual model installation,
GPU execution, driver compatibility, real-data migration, restore, power loss,
multiuser operation and production security remain unvalidated.

The pinned source inventory and deterministic focused ZIP allow byte comparison
across CI jobs. The release publication also reviews exact changed source and
assets against private markers; scanner findings require recorded dispositions.
Scanning supports manual review and does not prove absence of every secret or
operational clue. Actual instance data must remain private regardless of tests.
