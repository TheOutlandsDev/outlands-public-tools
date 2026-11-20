# Offline Order Revision Review Ledger Verifier

Verify saved order revision review events against their SHA-256 IDs, then report the newest decision. Events are sorted newest first, with descending event ID breaking timestamp ties. The tool uses local JSON and reads the ledger without updating it.

[Setup and fictional examples](SETUP.md) · [Downloads and validation](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-revision-review-ledger-verifier-v0.1.0)
