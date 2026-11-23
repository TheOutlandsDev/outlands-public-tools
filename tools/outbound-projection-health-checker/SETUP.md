# Run the Offline Outbound Projection Health Checker

Download the source ZIP and SHA256SUMS.txt together. On Windows, run Get-FileHash .\outbound-projection-health-checker-0.1.0.zip -Algorithm SHA256 in PowerShell and compare it with SHA256SUMS.txt. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. Run the fictional example with Python 3.12 or 3.15:

```text
python outbound_projection_health.py examples/fictional-status.json --at 2026-08-31T16:00:30Z --max-age-seconds 30
```

Use python3 on Ubuntu if that selects the intended interpreter. The CLI uses only the Python standard library.

The example prints {"healthy": true}. Its latest cycle failed, and its previous successful cycle remains fresh. Move the supplied time one second later and the result becomes unhealthy.

The saved UTF-8 status file must be at most 65,536 bytes and contain schema_version 1 and a time-zone-aware last_success_at timestamp. Supply a dated time with a UTC offset to --at and a nonnegative number of whole seconds to --max-age-seconds. The check accepts ages from 60 seconds in the future through the requested maximum age, inclusive.

The CLI reads the saved file and prints one boolean field. It exits 0 for a fresh recorded success, 1 for stale or unavailable health, and 2 for invalid command options. Missing, malformed, oversized and unsupported status files all produce unhealthy. The CLI runs without a live worker or database.

The validation records cover Windows and Ubuntu x64 on Python 3.12.16 and 3.15.2.
