# Run the Offline AI Hardware Quarantine Incident Classifier

Download the source ZIP and `SHA256SUMS.txt`. In PowerShell use `Get-FileHash .\ai-hardware-quarantine-incident-classifier-0.1.0.zip -Algorithm SHA256` and compare the digest with the checksum file. On Ubuntu run `sha256sum -c SHA256SUMS.txt`.

Extract the ZIP and open a terminal there. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2. The CLI uses the standard library.

Windows PowerShell

```powershell
python ai_quarantine_incidents.py examples/latched.json
python ai_quarantine_incidents.py examples/unlatched.json
```

Ubuntu

```sh
python3 ai_quarantine_incidents.py examples/latched.json
python3 ai_quarantine_incidents.py examples/unlatched.json
```

Supply a saved telemetry object with `ai.hardware_quarantine`. A literal JSON `true` in `latched` produces one critical AI incident. The summary includes up to 320 characters of reason text. Missing or unlatched quarantine data produces an empty incident list. A SHA-256 fingerprint covers the incident source, code, and summary.

The output retains the supplied quarantine object as evidence and adds the original AI-impact label and recovery guidance. It reads only the saved snapshot and makes no live hardware or server checks. The CLI has no controls for applying or clearing quarantine. Share output only where the supplied quarantine evidence may be shared.

Input is limited to 1 MiB of UTF-8 JSON. The CLI leaves the input unchanged and prints JSON to stdout. Invalid input returns exit code 2 and a diagnostic on stderr.
