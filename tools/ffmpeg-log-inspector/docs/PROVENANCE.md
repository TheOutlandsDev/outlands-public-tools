# Source provenance and license scope

This is freshly authored original source, tests and documentation, developed
with AI assistance for the owner of the OUTLANDS collection. The local starting
point was an owner-held webcam diagnostic helper that inspected FFmpeg frame
and clock text after a capture. Only that generic log-reading use case informed
this implementation. Its capture/device/process/event-log actions, machine
paths, concrete device names, real logs and private results were not copied.
The local original remains unchanged outside the public export.

The new implementation adds strict bounded UTF-8 snapshots, explicit parsing
modes, independent format summaries, structured block framing, unavailable/
malformed coverage, counter decrease observations, path/privacy boundaries,
exclusive report creation and generated portable CLI tests. Existing original
MIT collection file-I/O guard patterns were reused and adapted; their MIT
notice is retained in this module's [LICENSE](../LICENSE).

The original implementation, fictional fixtures and these documents are offered
under MIT. This does not relicense any input log, media, device software,
FFmpeg binary/library/source, PowerShell/.NET runtime or operating system.
No FFmpeg binary, media library, upstream parser implementation, firmware,
recording, real customer/project log or device configuration is distributed.
Authorship statements are not independent proof of every input's ownership.

## Primary format reference

The [official FFmpeg CLI documentation](https://ffmpeg.org/ffmpeg.html#Main-options)
was checked on 2026-10-25. It describes periodic statistics and program-friendly
key/value progress sequences closed by `progress=continue` or `progress=end`.
The inspector implements only the subset in [FORMAT.md](FORMAT.md); it does not
promise all current or historical FFmpeg diagnostic formats. Statistics text
and individual key availability can vary with build/options. The source was
not derived from a third-party parser, and no FFmpeg implementation was copied.

Only textual `out_time` is interpreted. Numeric `out_time_ms` and `out_time_us`
are ignored and counted rather than relying on historical naming/unit behavior.
No FFmpeg process is needed or invoked by the examples, tests or runtime CLI.

## Excluded private material

Public examples use invented Orchard log text. Actual logs can expose input
URLs, access tokens, file paths, devices, recording metadata and personal media
names. Keep them private; use synthetic minimal reproductions for issues.
The inspector's report omits raw lines and names but is not an anonymizer.

The optional Python source gate checks an explicit reviewed source allowlist,
UTF-8 text and hashes. Its exact manifest verifies selected bytes, not every
possible secret, legal rights in an input, or the correctness of a recording.
