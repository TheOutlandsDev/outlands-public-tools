# Contributions and suggestions

Use the Friendlies suggestion or bug form in the shared collection. Explain the
source/core issue or proposed workflow, exact versions/commit, and expected versus
actual behavior. Small fictional reproductions, readable tests and clearly scoped
solo gameplay evidence are welcome. No response time is promised.

Preserve MIT notices. Contribute only code you have rights to share, explain new
dependencies and their terms, and do not copy game/dependency/other-mod bodies.
Do not submit proprietary DLLs, firmware, profiles, credentials, private server
addresses or unredacted logs. Never treat fixture passes as gameplay acceptance.

Run the core tests and source_check.py. After reviewing changed source/paths,
regenerate SOURCE-MANIFEST.json with `python -B source_check.py --write-manifest`.
Manifest generation is not license/privacy review. Client changes also need a
local matching-SDK build; gameplay qualification is tracked separately.
