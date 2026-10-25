# Privacy and supported trust boundary

The journal stores complete event text in clear text. Console reports omit that
text and paths, but arguments, terminal/shell history, OS records and explicit
redirection can retain them. Files are not encrypted or anonymized. Keep real
journals and anchors in appropriately controlled private storage.

Use trusted, unchanged input files and parent folders. The client rejects
observed link/reparse components and detected size/time changes; those checks
have filesystem race windows and are not containment against hostile concurrent
replacement. A fresh failed write can leave a partial selected output. Inspect
it privately; the client never deletes an existing file as recovery.

An unanchored chain provides no independent author/authenticity guarantee. A
trusted head must be retained independently. No signature, access-control,
timestamp or permanent append-only store is implemented. Review FORMAT.md
before relying on a report's limited meaning.

For public bug reports, use fictional records and redact all identifying data.
Do not attach keys, certificates, internal journals, proprietary source, account
details or full private error paths. No automatic telemetry, network listener or
upload is part of this source.
