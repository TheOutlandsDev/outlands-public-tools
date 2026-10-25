# Validation record — 2026-10-25

The generated CLI harness runs with PowerShell 7.2+ on Windows and Ubuntu.
It starts bounded child copies of this inspector only; it does not invoke
FFmpeg, access capture devices, open media, contact the network or modify real
settings. All fixture logs are authored synthetic UTF-8 text or malformed bytes.
Generated test evidence stays in the explicitly supplied new private WorkRoot.

The final local Windows / PowerShell 7.6.5 run passed **55 generated CLI cases**
with one additional native symbolic-link case skipped for unavailable privilege.
The authored demo generator and actual example CLI passed separately. Native
symbolic-link creation can require a Windows privilege; a skipped native case
is reported explicitly and is not a pass. On Linux that refusal test is required;
`OUTLANDS_REQUIRE_SYMLINK_TEST=1` also requires creation on other platforms.
See the current [GitHub Actions results](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for the actual Windows/Ubuntu outcome rather than assuming a matrix passed.

Coverage includes no-BOM first-character retention, an optional real BOM, bare
CR/CRLF/LF records, final segments without newline, explicit modes, mixed modes,
supported numeric/clock formats, zero/N/A distinction, invariant French-culture
decimals, last/max counters and decreases, incomplete/duplicate/interrupted/
invalid progress blocks, end-marker limitations, ignored ambiguous numeric time
keys, raw unknown-value omission, phrase counts without raw lines, malformed
numbers/time/UTF-8, controls/ANSI/bidi, input/segment/key bounds, fresh-only
reports, attempted input-as-output, missing/relative/directory/link inputs,
help without reading inputs and source hashes retained after every inspected run.

The initial development check caught a .NET culture-sensitive BOM-prefix test
that treated the BOM as ignorable and stripped the first ordinary character.
The code now checks the first code point exactly. Authored no-BOM and BOM
fixtures exercise both paths; no failure was turned into a passing result.

The example generator is separately exercised against the real CLI. Its stderr
and structured examples produce observations; its review example intentionally
produces exit 1. These are parsing checks, not actual capture acceptance.

Limits are deliberately narrow. Tests do not prove all FFmpeg layouts, media
quality, device health, process completion, filesystem-race immunity, native
operation timeouts, power-loss recovery or secret removal. Native file I/O may
block on unsupported special files/unresponsive filesystems; use copied ordinary
stable logs. Parser success cannot replace a real recording/playback check.
