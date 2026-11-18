# Use the Offline Scheduled Task Preview

## Verify and extract the download

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/scheduled-task-preview-v0.1.0).
Compare the ZIP's SHA-256 with its checksum entry before extracting.

On Windows, use PowerShell.

```powershell
Get-FileHash .\scheduled-task-preview-0.1.0.zip -Algorithm SHA256
Expand-Archive .\scheduled-task-preview-0.1.0.zip .\task-preview
Set-Location .\task-preview\scheduled-task-preview-0.1.0
```

On Ubuntu, run

```bash
sha256sum scheduled-task-preview-0.1.0.zip
unzip scheduled-task-preview-0.1.0.zip -d task-preview
cd task-preview/scheduled-task-preview-0.1.0
```

Use Python 3.12 or 3.15. On Ubuntu substitute `python3` if needed.

## Preview the fictional tasks

```text
python -B -m scheduled_task_preview --input examples/preview.json --display-offset=-04:00
```

The output contains `runtime_status`, `next_action`, and `schedule`.
The example shows the warning at 11:45 AM and the restart at 12:00 PM.
It also shows the health refresh task as running and the runtime in
maintenance. Disabled and uninstalled tasks are omitted.

## Preview your own saved records

Use a UTF-8 JSON object up to 4 MiB with a `tasks` array and any saved
`runtime_status`, `automation_status`, `status`, or `issues` fields.
`issues` is an array of text when present. A UTF-8 BOM is accepted.
The CLI requires unique keys and finite numbers.

| Task field | Meaning |
| --- | --- |
| `installed`, `enabled` | Boolean flags. Both must be true to display the task. |
| `name` | Nonempty saved task name for a task included in the preview |
| `label` | Optional display label, defaulting to the saved name |
| `state` | Optional saved task state, with running tasks marked `RUNNING` |
| `next_run` | Optional ISO 8601 timestamp with an explicit time-zone offset |
| `warning_minutes` | Optional nonnegative integer applied to the saved next run |

When you provide a positive `warning_minutes`, the saved next run
is the warning time. The preview adds that interval to show the
expected restart. Use `Z` for UTC or a fixed offset such as `+05:30`
or `-04:00` for display. Select the offset appropriate for the time
you want to display. The report reflects the saved task state.

Valid input returns exit status 0 and prints JSON to stdout. Invalid
arguments, malformed timestamps, and unreadable or oversized files
return exit status 2 with a diagnostic on stderr.

## Verify the source and tests

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The validation records cover fresh extraction and copied CLI checks on
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
