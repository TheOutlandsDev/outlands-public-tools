# Changelog

## 1.0.0 — source qualification release

- Qualify the unchanged 1.0.0 runtime on pinned CPython 3.12–3.15 for Windows/Ubuntu.
- Preserve all 75 originals, the original HTTP fixture and five historical records;
  add thirty copied-runtime checks, exact source/archive pins and validation gates.
- Add an independently authored fictional loopback walkthrough with exact requests,
  complete plaintext session readback, context/retry and refusal-order checks.
- Publish the source ZIP, checksums, guide, validation and build manifest. No actual
  Ollama, model, inference, GPU, cloud isolation or real conversation is qualified.

The retained earlier [validation](docs/VALIDATION.md) and dependency/provenance
records use the historical 0.1.0 review label. This current release follows the
pre-existing `steven.__version__ = "1.0.0"` without changing runtime bytes.
