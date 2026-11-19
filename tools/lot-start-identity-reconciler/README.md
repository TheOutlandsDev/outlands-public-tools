# Offline Lot-Start Identity Reconciler

Join saved lot-start recommendations to last-lot mappings, verify the next ID,
and show the proposed sequence. Mappings without a queued recommendation appear
as reference rows.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-identity-reconciler-v0.1.0)
- [Setup guide and fictional inputs](SETUP.md)

The release preserves the original reconciliation and sequencing rules, with
four original tests using fictional data. It adds guards for duplicate
prefixes on either side. Qualification uses Python 3.12.16 and 3.15.2 on
Windows and Ubuntu with pinned Pydantic.
