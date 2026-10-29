# OUTLANDS | EML/MIME Inspector

Inspect a bounded strict MIME subset without rendering bodies or extracting attachments. Independent source CLI/library; Python 3.12/3.13,
standard library only, [MIT licensed](LICENSE).

## Fictional example

From the collection root (replace the EML example placeholder with a fully
spelled existing private directory outside the source tree):

```text
python -B tools/eml-mime-inspector/fictional_eml.py --out <new-external-directory>/fictional.eml
python -B tools/eml-mime-inspector/inspect_eml.py --input <new-external-directory>/fictional.eml
```

No inputs are discovered automatically. These examples contain only invented
records and reserved example.invalid addresses. No real mail, private application
source, templates, routing, endpoints, credentials or delivery records are bundled.
No provider adapter, network call, send, retry, process launch or target update.
Combined packages and browser applications are deferred.


## Supported EML subset

`inspect(raw)` accepts at most 2 MiB of CRLF-only, NUL-free 7-bit source;
998 bytes/line; root header block at most 64 KiB. The standard-library parser's
defects are refused. Each part requires explicit Content-Type; at most 32 total
parts, 16 children per multipart, depth 8, 64 unique headers per part and 8,192
characters per unfolded header. Duplicate singleton/MIME headers are refused.

Root headers: required From, To, Subject, MIME-Version: 1.0; optional Cc, Bcc,
Reply-To, Date, Message-ID, Content-ID, X-Reference, X-Category and supported MIME
headers. Other headers are refused. Nested parts accept MIME headers/Content-ID
only. Addresses follow the narrow bare-ASCII subset in message_core.py, comma
separated (32/group,64 total), without display names/comments/groups. Subject
must be nonempty and at most 160 ASCII source characters. Date, Message-ID and
Content-ID are opaque retained header syntax, not semantic validation. Encoded
words in subjects are not decoded into output. No authenticity/SPF/DKIM checks.

Exact supported Content-Type forms (case insensitive): `text/plain; charset=utf-8`,
`text/html; charset=utf-8` (or us-ascii), `application/octet-stream`,
`multipart/mixed; boundary="token"`, `multipart/alternative; boundary="token"`.
Charset is unquoted; boundary uses 1..70 ASCII alphanumerics/underscore/hyphen.
Only the single indicated parameter is accepted. No nested message/rfc822,
images, inline assets, MIME name parameters or arbitrary extension types.

Text supports 7bit or strict canonical base64; binary attachments require base64
and `Content-Disposition: attachment; filename="basename"`. Text attachments
may use that disposition too. Duplicate attachment names (case insensitive),
paths, reserved names, extended/encoded or duplicate parameters are refused.
Base64 strips CRLF only and must re-encode identically. No quoted-printable,
8bit, binary transfer encoding or arbitrary whitespace tolerance. Decoded text
must match the declared charset and contains no forbidden controls; LF/TAB and
normal CRLF are accepted. Total decoded bytes at most 2 MiB. Nonempty multipart
preamble/epilogue and broken boundaries are refused.

Default output exposes part positions, depths, types, sizes and decoded payload
hashes. It omits header values, filenames and bodies. **HTML is only hashed and
validated as text; it is never rendered, sanitized or certified safe to open.**
Nothing is extracted or followed. This deliberately refuses many ordinary emails;
it is a narrow inspection contract, not a general mailbox viewer or malware scan.


## Files, diagnostics and privacy

See [checked Windows/POSIX I/O](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). JSON parsing rejects duplicate keys, floats,
nonfinite numbers, invalid Unicode, excess depth/nodes and unknown fields.
Declared strings are generally at most 4,096 characters. Reports serialize as
ASCII JSON. `--out` creates a new external file only; parent must exist. No
overwrite, source-tree output or automatic cleanup/retry after write failure.
Failed writes may leave retained unconfirmed output; choose a new path.
Windows ACLs inherit from the chosen directory. Inputs must be trusted/quiescent.

Exit codes: 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption.
`--help` shows static usage; errors omit supplied values/paths. Default stdout
can contain private values or fingerprints. Output hashing and JSON escaping
provide no anonymization. Structural acceptance is not permission to publish
real inputs or reports, nor a secret/content scanner. No real delivery or
mail-client rendering is qualified.

From this tool directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
