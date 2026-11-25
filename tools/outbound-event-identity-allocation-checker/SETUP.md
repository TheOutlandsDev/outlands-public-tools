# Run the Offline Outbound Event Identity and Lot Allocation Checker

Download the source ZIP and SHA256SUMS.txt together. Compare the ZIP's SHA-256 with the checksum file. On Windows run `Get-FileHash .\outbound-event-identity-allocation-checker-0.1.0.zip -Algorithm SHA256`. On Ubuntu run `sha256sum -c SHA256SUMS.txt`.

Extract the ZIP and run the fictional example from its directory. The CLI uses the standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python outbound_event_identity_checker.py examples/outbound-event.json
```

Ubuntu

```sh
python3 outbound_event_identity_checker.py examples/outbound-event.json
```

Supply a JSON object with the fields in the example. The revision hash must be 64 lowercase hexadecimal characters, the row ID 24 lowercase hexadecimal characters, and the row version a positive integer. The lot IDs and quantities are two strings. Separate their values with whitespace, commas, or semicolons. Pair IDs and quantities in the original order.

The example reports a deterministic event ID and two lot allocations of 180 and 120. Repeating the same revision hash, row ID and version produces the same ID. The lot fields are checked separately and do not enter the hash.

The CLI reads at most 1 MiB of UTF-8 JSON and prints its report to stdout. Malformed inputs or ambiguous allocations return exit status 2 and a diagnostic. Output includes the lot IDs supplied in the input. The CLI leaves the input file unchanged and makes no database or network calls.
