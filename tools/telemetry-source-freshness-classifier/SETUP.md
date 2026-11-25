# Run the Offline Telemetry Source Freshness Classifier

Download the source ZIP and `SHA256SUMS.txt`. Compare the SHA-256 digest using `Get-FileHash .\telemetry-source-freshness-classifier-0.1.0.zip -Algorithm SHA256` in PowerShell or `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal in the extracted folder. The CLI uses the Python standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python telemetry_source_freshness.py examples/source-health.json
```

Ubuntu

```sh
python3 telemetry_source_freshness.py examples/source-health.json
```

The example reports two warnings. The inventory collector has a cached fallback, the storage collector has no valid fallback, and the fresh temperature collector produces no incident.

Supply a JSON object with a `source_health` object keyed by collector name. Each entry may include a `state` and related evidence. State matching ignores case. A collector object without a state is treated as unavailable. Non-object entries are skipped. An absent or empty `source_health` produces an empty incident list.

The classifier uses the supplied states. It makes no live checks and does not recompute freshness from timestamps. The output keeps each warning's collector evidence and adds the original impact text, guidance, and SHA-256 fingerprint. Share output only where the supplied evidence may be shared.

Input is limited to 1 MiB of UTF-8 JSON and 1,000 collectors. The CLI leaves the input unchanged, writes JSON to stdout, and returns exit code 2 for invalid input.
