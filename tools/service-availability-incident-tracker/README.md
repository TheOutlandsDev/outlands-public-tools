# Offline Service Availability Incident Tracker

Turn saved health-check results into an availability state and incident
durations. The tracker takes caller-supplied observations, tracks the worst
state reached, and records recovery. It uses the Python standard library.
Pass a state file to continue an incident across invocations.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/service-availability-incident-tracker-v0.1.0)
- [Usage guide with a fictional incident](SETUP.md)

The release preserves the original classification and transition logic
and all three original tests using fictional data. State persistence uses
a unique temporary file beside the selected state file and replaces the
destination after closing the temporary file.
