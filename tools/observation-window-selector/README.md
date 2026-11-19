# Offline Observation Window Selector

Validate a saved, newest-first list of up to 100 millisecond timestamps
and return the latest observed day as a midnight-to-midnight window.
Duplicates count as separate observations. An empty list returns no window.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/observation-window-selector-v0.1.0)
- [Usage guide and fictional inputs](SETUP.md)

The standalone selector retains the original row-validation and day-selection
rules and all five offline tests. It reads a local JSON file and uses the
Python standard library. Qualification covers Windows and Ubuntu with Python
3.12.16 and 3.15.2.
