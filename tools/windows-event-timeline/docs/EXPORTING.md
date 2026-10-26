# Saved event exports

The inspector reads saved metadata only. It does not query Windows, open native
EVTX/EVT files, collect camera streams or contact a computer. Use the generated
examples first. Real exports and reports stay private: even when reports omit
computer/payload fields, raw exports may contain them.

## Normalized JSON schema

```json
{
  "schema_version": 1,
  "events": [
    {
      "provider": "Example.Demo",
      "event_id": 100,
      "time_created": "2026-01-01T00:00:00.0000001Z",
      "channel": "Example/Diagnostic",
      "record_id": 1,
      "computer": "FictionalComputer",
      "version": 0,
      "level": 4
    }
  ]
}
```

Required fields are provider, event_id and time_created. See [FORMAT.md](FORMAT.md)
for optional fields, bounds, identity scope and exact time semantics. There are
no raw message/user-data fields in this schema. Unknown fields require coverage
and are not embedded in reports. Integer input values must be exact JSON
integers; do not round 64-bit IDs through floating-point serializers.

## Optional manual Windows XML export

This is a separate manual read of a selected local Windows channel, not part of
the inspector or its automated validation. It requires permission to read that
channel. Pick a short window and an external private directory you control.
The example reads at most 101 events and refuses to write if the chosen window
contains more than 100. It cannot prove full channel retention/completeness.
No real event query was run to validate this documentation.

Replace the destination with a new absolute filename whose parent exists. The
file is created exclusively; an existing destination is refused. The resulting
XML contains raw event payloads and machine data, so do not publish it.

```powershell
$destination = Join-Path ([System.IO.Path]::GetTempPath()) 'private-event-window.xml'
$filter = @{LogName='System'; StartTime=(Get-Date).AddMinutes(-10)}
$records = @(Get-WinEvent -FilterHashtable $filter -MaxEvents 101 -ErrorAction Stop)
if ($records.Count -gt 100) { throw 'Choose a smaller event window.' }
$xml = '<Events>' + (($records | ForEach-Object { $_.ToXml() }) -join "`n") + '</Events>'
$bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($xml)
$stream = [System.IO.File]::Open($destination, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
```

Then run the inspector with `--file` set to that absolute filename, `--format xml`
and a fresh absolute `--output` directory. Some valid Windows exports contain
payload/XML syntax outside this deliberately limited reader; the tool refuses
or marks unsupported data rather than guessing. Use the documented minimized
JSON metadata schema when full exported XML is outside the subset. Do not rename
an EVTX file to XML or assume a completed report establishes channel completeness.
