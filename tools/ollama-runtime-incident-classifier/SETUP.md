# Run the Offline Ollama Runtime Incident Classifier

Download the source ZIP and `SHA256SUMS.txt`. Compare the SHA-256 digest using `Get-FileHash .\ollama-runtime-incident-classifier-0.1.0.zip -Algorithm SHA256` in PowerShell or `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal in that folder. The CLI uses the Python standard library. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2.

Windows PowerShell

```powershell
python ollama_runtime_incidents.py examples/planned-off.json
python ollama_runtime_incidents.py examples/unavailable.json
```

Ubuntu

```sh
python3 ollama_runtime_incidents.py examples/planned-off.json
python3 ollama_runtime_incidents.py examples/unavailable.json
```

Supply a JSON snapshot with an `ai.ollama` object. Use a Boolean `healthy` and a string `expected_state`. The classifier treats `planned_off` case-insensitively. Other states follow the online rule.

| Expected state | Saved endpoint health | Result |
| --- | --- | --- |
| Online | Healthy | No incident |
| Online | Unhealthy | Endpoint unavailable warning |
| Planned off | Healthy | Unexpected runtime warning |
| Planned off | Unhealthy | No incident |

Missing state defaults to online, and missing health defaults to unhealthy, matching the source rule. Warning evidence includes the supplied Ollama fields and the original impact and guidance. Reports reflect the saved evidence and perform no endpoint probes or service actions.

Input is limited to 1 MiB of UTF-8 JSON. The CLI leaves the input unchanged, writes JSON to stdout, and returns exit code 2 for invalid input.
