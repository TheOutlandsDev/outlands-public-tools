# Offline Server Runtime Incident Classifier

Classify saved server observations as outages, maintenance, planned-off
mismatches, or automation and support warnings. The report includes an
incident fingerprint and details from each supplied observation. The CLI
uses the Python standard library and prints JSON.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/server-runtime-incident-classifier-v0.1.0)
- [Usage guide and fictional observations](SETUP.md)

The release preserves the three original server-focused cases and the
server classification rules. Qualification covers Windows and Ubuntu
with Python 3.12.16 and 3.15.2.
