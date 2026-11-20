# Offline Production Follow-Up Priority Reporter

Rank follow-up items from saved order demand allocation and shipment readiness reports. Operator results flag missing planning configuration and required lot starts. Program lead results identify missing lot evidence, clearance work and grouped transfers of completed panel lots.

[Setup and fictional walkthrough](SETUP.md) · [Download and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-follow-up-priority-reporter-v0.1.0)

The standalone tool accepts JSON from the two published upstream reporters. It preserves the original ordering and role assignment, and skips products with no remaining demand even when they have no due-date row. Workspace references are identifiers from the original reports. The CLI displays actions without executing them.
