# Provenance and publication scope

The starting workflow was the owner's 597-byte CMD game launcher. It checked a
fixed executable path, used a basename process check to avoid a duplicate, and
called Windows `start` with normal priority and a one-processor affinity mask.
The original private-path wrapper remains unchanged; its original-path/hash
record is retained privately outside this source export.

This public implementation was freshly authored with AI assistance to make that
workflow reusable. It introduces explicit inputs, a non-launching plan, native
suspended creation and readback, structured receipts, bounded waits, tests and
fictional examples. It is not a whole export of the old game installation or an
attempt to relicense any game/runtime material.

The owner authorized cleanup, testing and public MIT publication in OUTLANDS
Public Tools. Owner-reported personal authorship and this selected-source review
are not independent guarantees of exclusive authorship of unrelated historical
material. No required attribution or license notice was removed from the
selected original source.

Only the named original source, tests, documentation and generated/fictional
examples receive this folder's MIT grant. No game executable, proprietary asset,
save/profile, local machine inventory, original absolute path, application
configuration, private receipt or compiled runtime is included.

Microsoft's documented API contracts informed the original ctypes adapter; no
Microsoft implementation was copied. Python and Windows are supplied separately
and keep their own terms. Consult THIRD-PARTY-NOTICES.txt and
[dependency records](DEPENDENCIES.json).

The historical one-processor game workaround is a use-case origin, not a new
compatibility acceptance result. This release's validation uses original
disposable programs and simulated failure paths. Process creation and affinity
readback do not establish usable gameplay, stability or performance.
