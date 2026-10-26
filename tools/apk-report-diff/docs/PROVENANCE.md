# Provenance and MIT scope

The owner's local `inspect_ims_apks.sh` helper invoked AAPT2 against fixed APK
paths and filtered selected badging lines. That helper is preserved separately
and unchanged. Its generic use case inspired a fresh saved-report parser and
comparison implementation, not a copy of vendor APK contents or AAPT2 internals.

Public code, tests, guides and fictional generators are newly authored original
work; shared bounded input/report helpers and guard tests are first-party MIT
collection code. The implementation contains no original fixed device paths,
firmware, proprietary APK resources, real package inventories, credentials,
private captures or vendor repair recipes. Owner identification and selected
source review do not independently prove every historical source's authorship.

MIT covers this selected original implementation/docs/tests and generated
fictional examples. Python and separately installed AAPT2 retain their applicable
licenses. Android documentation and inspected text/APKs retain their rights.
No third-party implementation is bundled or relicensed, and inspection does not
grant rights to publish an input.

Primary background reviewed on 2026-10-26:

- [Official AAPT2 command and dump documentation](https://developer.android.com/tools/aapt2)
- [AOSP build history showing separately required/optional uses-library report lines](https://android.googlesource.com/platform/build/+/2b4d131e151a377282985f457133c1919708998b%5E2..2b4d131e151a377282985f457133c1919708998b/)

These sources explain producer context and format examples. The parser has its
own narrower documented grammar and no ported upstream implementation. Captures
are user-supplied observations; this tool cannot establish capture authenticity,
completeness, actual device behavior, app safety or installation compatibility.
