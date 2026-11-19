# Use the Offline Firewall Rule Evidence Checker

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/firewall-rule-evidence-checker-v0.1.0).
Compare the ZIP digest with its checksum before extracting into a fresh
directory.

PowerShell

```powershell
Get-FileHash .\firewall-rule-evidence-checker-0.1.0.zip -Algorithm SHA256
Expand-Archive .\firewall-rule-evidence-checker-0.1.0.zip .\firewall-evidence-demo
Set-Location .\firewall-evidence-demo\firewall-rule-evidence-checker-0.1.0
```

Ubuntu shell

```sh
sha256sum firewall-rule-evidence-checker-0.1.0.zip
unzip firewall-rule-evidence-checker-0.1.0.zip -d firewall-evidence-demo
cd firewall-evidence-demo/firewall-rule-evidence-checker-0.1.0
```

## Compare the fictional rules

Run with Python 3.12 or 3.15. Use `python3` if that is the name of your
interpreter.

```text
python -I -B firewall_evidence.py --input examples/allowed.json
python -I -B firewall_evidence.py --input examples/mismatch.json
python -I -B firewall_evidence.py --input examples/missing.json
```

The first example matches all declared fields. The second adds the Public
profile to a Private rule. The third has an empty saved rule list.

| JSON status | Meaning | Exit status |
| --- | --- | --- |
| `allowed` | One saved rule matches the declared fields | 0 |
| `mismatch` | Matching rule names were found and the saved evidence failed the scope checks | 1 |
| `missing` | The declared rule name was absent | 1 |

Invalid input exits with status 2 and a fixed diagnostic on stderr. The
comparison output contains only the status. Submitted names, interfaces,
addresses, and paths are omitted.

## Supply saved evidence

Use a regular UTF-8 JSON file with no byte-order mark and a size of at most
256 KiB. The examples show the complete input structure.

- `service` holds `firewall_rule`, `protocol` (`tcp`, `udp`, `6`, or `17`) and
  `ports`, a nonempty list of concrete port numbers.
- `interface_alias` and `local_ipv4` declare the expected local scope.
- `policy.rules` contains saved rule records. Each relevant record identifies
  the rule with `display_name` and supplies `enabled`, `direction`, `action`,
  `profile`, `protocol`, `local_ports`, `interface_aliases`, and `local_addresses`.

The checker selects an exact rule name and requires one enabled inbound allow
rule with the Private profile and the declared protocol. The port set must
match exactly. Saved ports can include comma-separated entries and bounded
inclusive ranges. The interface and local IPv4 address must match exactly.
The result describes the supplied rule evidence and its declared local scope.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

Read `VALIDATION.json` from the release for the Windows and Ubuntu
fresh-extraction results.
