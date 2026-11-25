# Run the Offline Telemetry Incident Lifecycle Replay

Download the source ZIP and `SHA256SUMS.txt`. In PowerShell run `Get-FileHash .\telemetry-incident-lifecycle-replay-0.1.0.zip -Algorithm SHA256` and compare the digest with the checksum file. On Ubuntu run `sha256sum -c SHA256SUMS.txt`.

Extract the archive and open a terminal in the extracted folder. The CLI uses the Python standard library and its bundled SQLite module. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python telemetry_incident_replay.py examples/incident-lifecycle.json
```

Ubuntu

```sh
python3 telemetry_incident_replay.py examples/incident-lifecycle.json
```

The fictional cooling incident starts active, is acknowledged, moves to monitoring after one clean observation, then resolves after the second. A clear before resolution removes zero rows. The final clear removes the resolved incident and preserves one active and one monitoring incident.

## Recording format

Set `clean_samples` from 1 to 100 and supply 1–100 `steps`. Begin with a `snapshot` step containing a saved snapshot and its incident list. Include `generated` with a time-zone offset and an `overall_status` string. Use strictly increasing times. An empty incident list represents a clean observation. Each candidate supplies a source, code, severity, summary and evidence object. Its SHA-256 fingerprint covers the original source, code and summary.

An `acknowledge` step takes the chosen fingerprint. A `clear_resolved` step takes no other fields. Use the fingerprints in the example or run a recording with only its snapshot steps first to obtain your own fingerprints. The report lists incident states and clean counts after each action and retains full evidence for incidents remaining at the end.

Steps use the recorded observation times for acknowledgement and retention. The original seven-day snapshot retention is relative to the latest observation in the replay. The CLI uses a fresh temporary directory for SQLite and removes it when finished. It takes no database path and leaves the input unchanged. It prints JSON to stdout and returns exit code 2 for invalid input. Use a recording up to 1 MiB with at most 100 distinct incident fingerprints.
