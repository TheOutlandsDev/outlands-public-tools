# OUTLANDS EML/MIME Inspector — 0.1.0

Inspect an explicit local EML file against a deliberately narrow MIME subset.
The summary records structure, decoded byte counts and SHA-256 fingerprints;
it never renders bodies, extracts files, sends messages or follows resources.
Original [MIT source](LICENSE), Python 3.12 or newer, standard library only.

## Download and fictional example

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/eml-mime-inspector-v0.1.0):
source ZIP, checksums, executable guide, public validation JSON and build manifest.
The ZIP contains 28 reviewed source files plus their manifest, 29 members. Python,
environments, real mail, mailboxes, attachments, generated reports and raw logs are
excluded. Verify checksums, extract into a fresh owned folder and keep all five
runtime/generator files together. No pip package, GUI, admin, login or mail provider
is needed for the fictional examples.

From this module directory, after selecting an existing absolute private parent
outside source in `$privateWork`:

```powershell
python -E -s -B fictional_eml.py --out "$privateWork/fictional.eml"
python -E -s -B inspect_eml.py --input "$privateWork/fictional.eml"
python -E -s -B inspect_eml.py --input "$privateWork/fictional.eml" --out "$privateWork/fictional-summary.json"
```

For POSIX shells use your selected `python3` with the same arguments. Both output
files must be new and their parents must already exist. The first inspection
prints the summary; `--out` writes the same compact ASCII JSON to a fresh file
and prints only `{"status": "PASS", "report_written": true}`. No automatic input
discovery or extraction occurs. The [executable guide](USAGE.md) supplies detailed
fictional accepted/refused cases and independently verifies exact bytes/hashes.

## Accepted subset and deliberate refusals

Source must be nonempty, at most 2 MiB, NUL-free 7-bit data with CRLF line endings
and at most 998 bytes per line. The root header block is at most 64 KiB. Detected
standard-library email-parser defects are refused. Each part requires an explicit
Content-Type. Bounds are 32 total parts, 16 children per multipart, depth 8,
64 unique headers per part and 8,192 characters per unfolded header.

Root From, To, Subject and `MIME-Version: 1.0` are required. Optional headers are
Cc, Bcc, Reply-To, Date, Message-ID, Content-ID, X-Reference, X-Category and the
supported MIME headers. Nested parts accept only MIME headers/Content-ID. Other
headers, including ordinary Received trace headers, are refused. No duplicate
header is accepted. Bare ASCII addresses only: no display names, groups or
comments; up to 32 recipients/group and 64 total, with casefold-duplicate recipient
addresses refused across To/Cc/Bcc. Subject is nonempty and at most 160 ASCII
source characters. Optional date/ID text is not an authenticity or delivery check.
Encoded-word subjects are not exposed/decoded into output.

| Content-Type | Required form |
| --- | --- |
| `text/plain`, `text/html` | One unquoted `charset=utf-8` or `charset=us-ascii`. |
| `application/octet-stream` | Base64 plus an attachment disposition; no charset. |
| `multipart/mixed`, `multipart/alternative` | One quoted boundary of 1–70 ASCII alphanumeric/underscore/hyphen characters. |

Media/parameter names are matched case-insensitively, but the supported spelling
and parameter shape remain restricted. No extra type/name parameters, images,
inline assets, nested `message/rfc822` or extension media types are supported.
Text uses 7bit or strict canonical base64. Base64 removes CRLF only and must
re-encode identically; spaces/tabs and noncanonical pad bits are refused. No
quoted-printable, 8bit or binary transfer encoding is supported. Decoded text
must match its charset and permitted controls. Decoded byte totals are bounded;
nonempty multipart preambles/epilogues and broken structures are refused.

Attachments require exactly `Content-Disposition: attachment; filename="basename"`.
Names use the bounded ASCII basename subset; traversal, reserved names, extended/
encoded/duplicate parameters and case-insensitive duplicate attachment names are
refused. A text attachment can be supported. Filename validation does not open
that name on disk, extract content or establish that content is safe.

This intentionally refuses many ordinary messages. It is not a general email
viewer, mailbox parser, MIME conformance certificate, spam/malware scanner or
provider adapter. It does not check SPF/DKIM/signatures, authenticity, attachment
safety, delivery, input rights or mail-client compatibility.

## Summary, privacy and native file guards

The summary has a format tag, source SHA-256, ordered part positions/depths,
media types, child counts, attachment booleans and decoded leaf byte counts/hashes.
Header values, body text, attachment names and input filenames are omitted.
There is no include-details switch. `--out` changes the destination, not privacy
fields. Hashes, sizes and structure can identify private messages/attachments;
field omission and JSON escaping are not anonymization or permission to publish.

HTML is validated/hashed as text, never rendered or sanitized. Remote links/images
remain uninterpreted source text. Nothing is extracted, sent, fetched or opened
through a mail provider. A PASS means this supported subset was accepted, not that
the message or attachment is trustworthy/safe to open elsewhere.

Select trusted quiescent regular single-link files and ordinary local parents.
The [historical I/O contract](IO-SAFETY.md) documents retained Windows handles or
POSIX directory-relative descriptors, link/identity/size checks and exclusive
fresh output. Inputs are explicit; there is no drive/mailbox enumeration. Windows
refuses UNC/device/alternate-stream/ambiguous or observed short-name routes and
reparse paths. POSIX uses no-follow descriptor traversal. The primary stream is
read; alternate private data is not enumerated or certified absent.

No existing output is replaced. Source-tree output is refused, and no parent
directory is created automatically. Relative paths can be resolved from the
chosen working directory; use explicit absolute paths for reviewable examples.
Shell redirection is controlled by the shell and lacks `--out` protections.
POSIX requests mode 0600; Windows inherits parent permissions. No ACL secrecy,
encryption, rights scrub or full metadata-preservation claim is made.

Interrupted/failed writes can leave partial or complete-looking unconfirmed output;
it is retained, never silently deleted/reused. Review privately and choose a new
destination. Sampled identities/hashes are not an adversarial lock, hostile-parent
sandbox, atomic multi-file snapshot, power-loss durability or universal rollback.
Parser bounds are application checks, including checks after standard-library
tree parsing; they are not OS memory/CPU limits or hard I/O deadlines.

Accepted inspection/generation exits 0. Refusal exits 2 with fixed
`{"status":"ERROR","code":"..."}` diagnostics, omitting supplied paths/values.
Interruption exits 130. The shared wrapper reserves exit 1 for other result
statuses, but this MIME inspector currently returns PASS or refusal rather than
a partial REVIEW_REQUIRED summary. Static `--help` does not inspect mail.

## Qualification and contributions

The [qualification contract](docs/QUALIFICATION.md) preserves all 52 originals
and adds thirty copied-runtime CLI checks per Windows/Ubuntu Python 3.12–3.15
lane. Actual release `VALIDATION.json` records passes/skips separately. The
[historical validation](VALIDATION.md), [origins](ORIGINS.md) and
[I/O safety record](IO-SAFETY.md) remain unchanged.

Report a fictional reproduction through [GitHub Issues](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Include exact source/Python/OS versions, commands and fixed errors. Exclude real
messages, addresses, headers, bodies, attachments, private paths, logs and provider
credentials. Structural acceptance does not establish rights to share an input.
