# Offline WIP Supply Normalizer

Prepare saved work-in-progress quantities for a planning review. The tool applies
a configured loss at selected steps, totals completed parts, and reports SHA-256
digests for the prepared rows and configuration.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/wip-supply-normalizer-v0.1.0)
- [Setup guide and fictional inputs](SETUP.md)

The release retains the four original normalization tests with fictional data.
Qualification uses Python 3.12.16 and 3.15.2 with pinned Pydantic on Windows and
Ubuntu.
