# Offline NVIDIA Telemetry Output Parser

Read saved NVIDIA GPU query output and produce a JSON report with device
readings, driver metadata and optional PCIe replay counts. The CLI runs
with Python's standard library and reads the two files you name.

- [Source ZIP, SHA-256 checksums and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/nvidia-telemetry-output-parser-v0.1.0)
- [Usage guide and fictional example](SETUP.md)

Qualification covers Python 3.12.16 and 3.15.2 on Windows and Ubuntu x64.
The package retains the original parser and a shared code path for its
live collector. The three original test cases use fictional hardware
details and a mocked command launcher. The CLI and qualification require
no GPU or NVIDIA utility.
