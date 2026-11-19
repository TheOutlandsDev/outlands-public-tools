# Offline Incident Evidence Bundle Builder

Collect three saved diagnostic JSON files and selected text attachments in
one ZIP. The builder masks recognized secret fields and writes a manifest
with each member's byte count and SHA-256 digest.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/incident-evidence-bundle-builder-v0.1.0)
- [Usage guide and fictional inputs](SETUP.md)

This edition retains Portable OpsKit's original CLI test for the four core
ZIP members, using fictional saved diagnostics. It uses the Python standard
library. Qualification covers Windows and Ubuntu with Python 3.12.16 and
3.15.2.
