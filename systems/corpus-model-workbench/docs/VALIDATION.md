# Fictional validation and limits

The automated suite exercises the complete app with fresh disposable stores:
deduplication/provenance, benchmark and duplicate-group holdouts, four-check
approval, FTS, separate SFT/RAG exports and independent hash checks, SQLite
backup/schema/version/sidecar refusal, JSON/gzip bounds, exclusive outputs,
workspace/source boundaries, session locks, interrupted-run recovery, fictional
model comparisons/scores/vectors/discussions, prompt caps, model error redaction,
and the real loopback HTTP UI's Host/token/Origin/error rules.

CI runs Python 3.12/3.13 on Windows and Ubuntu. Qualification requires 81
passing core methods and 22 passing actual Chromium methods in every job, plus
one visible opposite-platform core skip. All six native link/junction cases and
the real child termination/recovery case must pass with `WORKBENCH_REQUIRE_LINKS=1`.
The controlled local Windows core run discovered 82 methods: 75 passed and seven
skipped (six native filesystem fixture limitations and one POSIX-only case).
Native CI evidence, not local skips, determines publication readiness.

The end-to-end demo uses two explicitly fictional model names/digests and fixed
fake answers, deterministic fake vectors and invented scores. It verifies app
orchestration and review boundaries, not model inference, quality, training or
provider compatibility. No installed service, real record, historical store or
original program instance is opened. API tests use an ephemeral loopback server. Actual local model-client tests verify proxy bypass, redirect refusal and non-finite response rejection. A real child-process termination test verifies stale-lock recovery without replay.

The separate Chromium suite operates the real UI against fictional fresh stores.
It covers the complete import/review/export/backup workflow, context pin changes,
late holdouts, fake model comparisons and manual scoring, discussions and pending
queue, vectors and revocation, lost replies, busy actions, restart, literal markup,
invalid files, filters, keyboard input and a 390-pixel viewport. Wide, model,
discussion and narrow screens are captured for visual inspection before release.
API-only tests are kept separate from this browser evidence. Actual model installation,
GPU execution, driver compatibility, real-data migration, restore, power loss,
multiuser operation and production security remain unvalidated.

The pinned source inventory and deterministic focused ZIP allow byte comparison
across CI jobs. The release publication also reviews exact changed source and
assets against private markers; scanner findings require recorded dispositions.
Scanning supports manual review and does not prove absence of every secret or
operational clue. Actual instance data must remain private regardless of tests.

The hardening regressions were also exercised against an isolated copy of the
previous public source; their failures were retained privately. See
[changes and compatibility](HARDENING.md). No assertion, native fixture requirement,
source audit rule or browser timeout was relaxed to obtain a pass.
