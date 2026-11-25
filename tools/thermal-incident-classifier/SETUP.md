# Run the Offline Thermal Incident Classifier

Download the source ZIP and `SHA256SUMS.txt`. Compare the SHA-256 digest using `Get-FileHash .\thermal-incident-classifier-0.1.0.zip -Algorithm SHA256` in PowerShell or `sha256sum -c SHA256SUMS.txt` on Ubuntu.

Extract the ZIP and open a terminal there. Qualification used Windows and Ubuntu x64 with CPython 3.12.16 and 3.15.2. The CLI uses the standard library.

Windows PowerShell

```powershell
python thermal_incidents.py examples/thermal-snapshot.json --thresholds examples/thresholds.json
```

Ubuntu

```sh
python3 thermal_incidents.py examples/thermal-snapshot.json --thresholds examples/thresholds.json
```

The fictional example reports a CPU warning at 75 °C, a storage critical incident at the supplied 60 °C threshold, and a GPU critical incident at 88 °C. The static TjMax reading is skipped.

Supply a snapshot with readings under `system.hardware_sensors` and `gpus`, using the example shape. Temperatures are in Celsius. Omit `--thresholds` to use the original defaults, 75/85 °C for CPU and storage and 75/88 °C for GPU. A threshold file can override any `cpu`, `storage`, or `gpu` key ending in `_warning_c` or `_critical_c`. A reading exactly at the warning threshold warns. A reading exactly at the critical threshold is critical.

The classifier evaluates the supplied snapshot without contacting devices. GPU evidence includes the supplied GPU object. Each file is limited to 1 MiB of UTF-8 JSON and the snapshot to 1,000 combined readings. The CLI leaves input files unchanged, writes JSON to stdout, and returns exit code 2 for invalid inputs.
