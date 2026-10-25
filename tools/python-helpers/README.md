# Python Helpers

Small Python 3.12+ standard-library helpers, adapted from original neutral coding examples:

- `load_json_object(path, max_bytes=...)` reads a bounded UTF-8 JSON object, rejects nonstandard numeric constants, and reports fixed errors without paths or content.
- `redact_structure(value, max_depth=...)` makes a separate JSON-like structure, redacting values under a documented sensitive-key set in nested mappings/lists. It normalizes key case and dash/underscore variants and rejects excessive nesting or unsupported values.

The redactor does not inspect free text, discover unknown key names, remove identities, clear business information, or make arbitrary data safe to share. The loader accepts a caller-selected trusted path and does not act as a filesystem sandbox. Caller-owned input, output and logs remain private. Import this module explicitly from its directory; no installer or background service is provided.

MIT licensed; see [licensing](../../LICENSING.md) and [validation](../../docs/BATCH-6-REVIEW.md).
