# Offline Firewall Rule Evidence Checker

Compare a saved Windows firewall rule with a declared inbound allow rule.
The checker compares protocol, profile, ports, interface, and local IPv4
address and returns a short status report.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/firewall-rule-evidence-checker-v0.1.0)
- [Usage guide and fictional inputs](SETUP.md)

The release retains all three original offline tests with fictional rule
evidence. Qualification covers Windows and Ubuntu with Python 3.12.16 and
3.15.2 using the standard library.
