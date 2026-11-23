# Run the Offline Outbound Projection Status Reporter

Download the source ZIP and SHA256SUMS.txt together. On Windows, run Get-FileHash .\outbound-projection-status-reporter-0.1.0.zip -Algorithm SHA256 in PowerShell and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Use Python 3.12 or 3.15. The CLI uses only the Python standard library.

```text
python outbound_projection_status.py examples/accepted-outcome.json
```

Use python3 on Ubuntu if that selects the intended interpreter. The fictional outcome produces an accepted status with a last-success timestamp and zero consecutive failures. To evaluate a failure against a saved prior result, pass that result explicitly:

```text
python outbound_projection_status.py examples/failed-outcome.json --prior-status previous-status.json
```

The outcome needs last_result and an attempted_at timestamp with a UTC offset. Accepted outcomes also need projected_at, projection_run_id, and the three nonnegative event counts shown in the example. Failed outcomes need a failure_category of projection or unexpected. Timestamps in the report use UTC.

A failure retains a valid prior last-success timestamp and increments the prior failure count. Without a readable schema-version-1 prior record, it starts from no previous success and a count of zero. A success records projected_at and resets the count. The report retains the original schema and status labels and includes only its defined fields. Authentication data, shipment notes, and operator details supplied as extra fields are omitted.

The CLI prints the resulting JSON and leaves the input files unchanged. To use the result in the Offline Outbound Projection Health Checker, save the printed JSON as a separate status file. Exit status is 0 when the tool emits a status, including a recorded failure, and 2 for an invalid outcome.

The validation records cover Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
