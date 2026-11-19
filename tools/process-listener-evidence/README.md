# Offline Process and Listener Evidence Checker

Check saved process and listener evidence against an expected executable
or release directory. The report identifies a unique matching process and
checks whether it owns each declared TCP or UDP listener.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/process-listener-evidence-v0.1.0)
- [Usage guide and fictional examples](SETUP.md)

The CLI uses the Python standard library and reads a local JSON file.
The qualification workflow targets Windows and Ubuntu with Python
3.12.16 and 3.15.2.
