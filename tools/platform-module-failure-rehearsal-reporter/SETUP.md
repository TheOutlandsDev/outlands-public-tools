# Run the Offline Platform Module Failure Rehearsal Reporter

Download the source ZIP and SHA256SUMS.txt. In PowerShell, run Get-FileHash .\platform-module-failure-rehearsal-reporter-0.1.0.zip -Algorithm SHA256 and compare it with the checksum file. On Ubuntu, run sha256sum -c SHA256SUMS.txt.

Extract the ZIP and open a terminal in the extracted folder. The reporter uses Python's standard library.

Windows PowerShell

```powershell
python platform_rehearsal.py examples/fictional-registry.json
python platform_rehearsal.py examples/fictional-registry.json --simulate sample-inventory
python platform_rehearsal.py examples/fictional-registry.json --simulate all
```

Ubuntu

```bash
python3 platform_rehearsal.py examples/fictional-registry.json
python3 platform_rehearsal.py examples/fictional-registry.json --simulate sample-inventory
python3 platform_rehearsal.py examples/fictional-registry.json --simulate all
```

| Scenario | Available | Simulated unavailable | Planned |
| --- | ---: | ---: | ---: |
| Baseline | 15 | 0 | 1 |
| One business module | 14 | 1 | 1 |
| All business modules | 1 | 14 | 1 |

In the all-business-module scenario, the available row is platform-shell. The planned module keeps its PLANNED status in every scenario. Running the baseline again produces the same report. Unknown IDs, planned IDs, and platform-shell are refused as single-module simulation targets.

## Registry and output

Use the fictional registry as a template. Save it as UTF-8 JSON, up to 1 MiB. Provide contract_version, status, platform_name, organization_name, modules, and data_services.

Each module has a unique module_id, a display_name, a lifecycle, a failure_mode, a health_endpoint that begins with /health/, a data_stores list of registered service IDs, and a navigation.items list. Each navigation item supplies href and description. The first item supplies the row's primary link and description. Use an empty list for modules without an entry.

Use CURRENT_EMBEDDED and CURRENT_EMBEDDED_READ_ONLY for current modules and PLANNED_DISABLED for planned modules. Include one current platform-shell with failure_mode set to SHELL_REMAINS_AVAILABLE and no required module dependencies. ISOLATED_UNAVAILABLE_CARD is the other supported failure mode. Each data service needs a unique service_id and may include metadata for the report. The ID all is reserved for the all-business-module scenario.

The CLI prints JSON with simulation, shell_available, summary, modules, and data_services. The report uses the saved registry declarations and the selected scenario. The command leaves the input file intact. Success exits 0. Invalid input or an invalid target exits 2.

Qualification used Windows and Ubuntu x64 with Python 3.12.16 and 3.15.2.
