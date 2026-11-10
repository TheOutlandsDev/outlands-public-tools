# Validation boundary for version 1.1.0

The local Windows 11 baseline used Python 3.15.2, Node 26.13.0, and Temurin
JDK 27.0.1. The deterministic checks passed:

- Thirty installer/evaluation/pairing tests, with no skips: previews, conflicts,
  exact-byte backups, drift refusal, rollback, interrupted writes, unsafe
  paths, reparse-point refusal, template hashes, and model inventory checks.
- PowerShell preview/install/verify/restore using paths containing spaces.
- Python order/stock tests, Node discount tests, and Java compilation and
  stock acceptance checks, without third-party fixture dependencies.
- Deliberately broken Python boundary logic and Node rounding were detected.
- The bug-fix scorer rejected changed test files and used a separate oracle.
- Repository documentation/JSON checks returned no findings.
- Four in-memory OpenAI Python 3.48.0 request/response checks: Runtime and
  Mantle with dummy bearer and SigV4 auth, socket creation blocked.
- The laptop inspection's small metadata-command boundary and unreadable
  policy handling were checked without launching discovered applications.
- All six skill frontmatters passed authoring validation.

The [CI workflow](../../.github/workflows/kiro-dev-kit.yml) repeats the
installer, PowerShell, language-fixture, and documentation checks on Windows
and Ubuntu with the stated language versions. Consult the actual run result;
the presence of a workflow file does not establish a completed run.

The standalone inspection targets Windows PowerShell 5.1 and PowerShell 7.
Its policy checks can be unreadable on a managed device; this is reported as
unknown and never as permission to install. The SDK probe does not resolve
real credentials, test IAM or SSO, discover model availability, contact AWS,
or establish reachability through company networking.

The reparse-point test simulates the Windows attribute without requiring
symlink privileges. It is not proof against all filesystem races, native
alias behavior, or concurrent writers. The installer rejects known links and
reparse components and scopes writes to the selected project; use an ordinary
local directory and stop concurrent changes during installation or restore.

No live Kiro authentication, agent loading, model invocation, tool delegation,
reviewer quality, or handoff recall is established by these checks. The
readiness report retains NOT_RUN for those states. Follow
[ACCEPTANCE.md](ACCEPTANCE.md) in the managed Kiro environment. Exact parity
with Codex, all employer projects, the existing 76-tool wheel collection, and
every third-party library on Python 3.15 are not claimed.
