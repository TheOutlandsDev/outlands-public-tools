# Validation record — 2026-10-25

Local Windows / Python 3.12.7: **54 unittest methods discovered, 50 passed and
four skipped**, with no failures/errors. Three skips require native symlink
creation privilege unavailable to this local account. The fourth requires a
POSIX FIFO. Linux CI must execute the symlink and FIFO cases; a Linux symlink
setup failure is a failure, not a skip. `VPD_REQUIRE_SYMLINK=1` can require native
symlink fixtures elsewhere when the environment supplies the privilege.

Tests cover:

- Supported structural counts, bin/project/unclassified roles and explicit
  incomplete bin/timeline coverage; unknown paths are not silently called media.
- Strict duplicate-key, UTF-8, NaN/Infinity, number-token/exponent, depth,
  node/key/string/reference/project/mapping/report bounds.
- Default path/title/unknown-pointer omission, explicit path-text expansion,
  HTML escaping/control display and absence of script/file-opening links/assets.
- Exact project hashes, stale mapping rejection, strict fields and schemas,
  project-record/unknown-role refusal, validation before metadata observations.
- Portable relative path rules, traversal/absolute/URL/device text separation,
  case/NFC collisions and explicit reuse of one target by multiple references.
- Missing, unavailable, linked, nonregular and non-directory component outcomes;
  metadata-only checks with file-opening calls mocked to fail.
- Regular/stable input reads, observed mutation failure, source bytes unchanged,
  FIFO/link refusal, fresh-only output, output boundary/size guards, partial-new-
  output failure and independent report manifest/hash readback.
- Actual CLI inventory/error behavior and invented missing/complete mapping
  walkthroughs using empty placeholders.

A separate actual CLI walkthrough generated the complete fictional fixture and
produced three report files with three references, two mapped metadata attempts,
zero coverage issues and `NO_MAPPING_FINDINGS`. No media content was opened;
the two observed files were empty placeholders. This checks CLI/report plumbing,
not media validity or successful editor recovery.

The collection workflow runs these fixtures with Python 3.12 and 3.13 on Windows
and Ubuntu. See [GitHub Actions](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for hosted outcomes and platform skips. Local skips are not passes.

No actual owner project, recording, private inventory, native editor, game,
camera/microphone, device or network procedure was used as an acceptance test.
Observed VPD schema positions and authored fixtures do not establish compatibility
with every editor/version, all reference kinds, project playback, clip integrity,
rendering, relinking, archival completeness, redistribution rights, adversarial
filesystems or power-loss recovery.
