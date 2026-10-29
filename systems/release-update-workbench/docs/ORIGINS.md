# Public source and methodology origins

This is a fresh neutral application using existing public first-party components and invented fixtures. No private original launcher/updater, business/customer code, operational setup/configuration, user/player record, credential/key, real host path/endpoint/topology, game/mod asset, raw log or third-party/runtime binary is selected or exported. Original source families retain separate clearance.

`releases/vendor/preflight.py` and `preflight_windows.py` are unchanged public snapshots of [Release Preflight](../../../tools/release-preflight/README.md). The application uses their guarded directory/hash/inventory mechanisms for complete explicitly selected package capture. It does not invoke their CLI or perform target updates. The new strict manifest/launcher contract is a bounded subset; launcher acceptance is structural only.

`releases/vendor/lock_diff.py` is an unchanged public snapshot of [Dependency Lock Diff](../../../tools/dependency-lock-diff/README.md). Only its pure parser/comparison functions are used; its file/CLI entrypoints are not invoked. Its grammar, declaration-only scope and absence of package downloads/resolution/artifact/advisory/upgrade-direction checks are preserved.

The unchanged private file/store native helpers, exact schema/runtime boundary, deterministic source packager and token/Host/Origin loopback patterns come from the public [Environment & Setup Workbench](../../environment-setup-workbench/README.md). Candidate capture orchestration, descriptor/result contracts, file difference model, conservative blockers, manual plans, approval/revocation transitions, interface and fictional tests are newly authored neutral code.

MIT notices remain under TheOutlandsDev. Python/SQLite/native APIs and optional test-only Playwright/Chromium/PowerShell dependencies are separately supplied under their own licenses. No third-party asset is bundled. The source manifest and exact publication audit apply to this selected source release, not original programs or future private instances.
