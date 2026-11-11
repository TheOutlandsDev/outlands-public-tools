# Changelog

## 0.2.0

- Set .NET 10 LTS (`net10.0`) as the default target with pinned SDK 10.0.404;
  added explicit .NET 11 (`net11.0`) builds using pinned SDK 11.0.100.
- Added a standalone source-ZIP release, exact source inventory, pinned
  official SDK archive metadata and standard-library-only Python helpers.
- Added qualification for four Windows/Ubuntu x64 SDK/runtime lanes and eight
  Python 3.12–3.15 source/build-helper lanes. Actual pass/failure/skip totals
  are recorded in the release `VALIDATION.json`.
- Added standalone build, private-workspace and anchored-verification guides.
  A built CLI needs its app files and matching .NET runtime; Python, network
  access, a model and an account are not needed to use it.
- Preserved version 1 JSONL/hash rules, independent golden hashes, input
  preservation, fresh outputs and documented trust/filesystem limits.
- Kept original private material, real journals, generated builds, runtime/SDK
  binaries, dependency binaries and raw diagnostics outside the release.

## 0.1.0 — 2026-10-25

- Added original .NET 8 offline JSONL hash-chain creation and verification.
- Added new-version append with validation and exclusive output creation.
- Defined strict versioned hashing/encoding/size rules and trusted-head/count
  checks, with explicit unanchored consistency limits.
- Added generated mutation, parsing, I/O and CLI fixtures, an independent golden
  hash, fictional examples, detailed instructions and suggestion forms.
- Kept historical source, wallet/network mechanisms and private records outside
  the public source selection.
