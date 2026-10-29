# OUTLANDS | Message Envelope Checker

Check bare-address envelopes, restricted headers and declared attachment manifests. Independent source CLI/library; Python 3.12/3.13,
standard library only, [MIT licensed](LICENSE).

## Fictional example

From the collection root (replace the EML example placeholder with a fully
spelled existing private directory outside the source tree):

```text
python -B tools/message-envelope-checker/envelope.py --input tools/message-envelope-checker/examples/envelope.json
```

No inputs are discovered automatically. These examples contain only invented
records and reserved example.invalid addresses. No real mail, private application
source, templates, routing, endpoints, credentials or delivery records are bundled.
No provider adapter, network call, send, retry, process launch or target update.
Combined packages and browser applications are deferred.


## Contract and limits

`check(raw, include_values=False)` accepts exact JSON fields shown in the fictional
example. `format` is `outlands-message-envelope-v1`; sender is required, reply_to
is a bare address or null. `to`, `cc`, `bcc` are lists, each at most 32, combined
1..64. Duplicates across lists are refused conservatively using case folding.
Local-part case is otherwise preserved; domains are lowercased. Only ASCII
dot-atom local parts (1..64) and dotted DNS-shaped domains are supported. No
display names, comments, groups, quotes, Unicode domains, domain literals or local hostnames.
ASCII DNS labels, including punycode, receive syntax checks only.
This syntax subset does not establish deliverability, authorization or ownership.

Subject is nonblank, at most 160 characters; controls/format characters including
CR/LF are refused. Only exact `X-Reference` and `X-Category` extension headers
are accepted with nonblank values of at most 160 characters. No routing,
authentication or MIME header overrides. No header serialization occurs.

Attachments are **declarations**, not file paths: at most 16; fields `name`,
`media_type`, `bytes`, `sha256`. Names are unique ignoring case and match a
portable ASCII basename subset (80 characters, no traversal/reserved names).
Types: text/plain, text/csv, application/json, application/pdf or
application/octet-stream. Exact nonboolean byte counts: 0..16 MiB per item,
at most 32 MiB total; lowercase SHA-256. No files are opened or hashes verified.
Default report includes only counts and the raw input pin. `--include-values`
explicitly exposes normalized addresses, BCC values, subject, headers and manifest.


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
