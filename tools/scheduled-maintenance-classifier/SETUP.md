# Offline Scheduled Maintenance Classifier

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. It uses Python's standard library.

## Review the fictional observation

```
python scheduled_maintenance.py --input examples/maintenance.json
```

Expect warning status and a runtime status of maintenance. The Example Daily Restart task is enabled and running, and its saved start time is five minutes before the observation. The maintenance explanation appears in the issues list.

## Input and output

Use a UTF-8 JSON file of at most 2,000,000 bytes. Include the following fields.

- observed_at is the observation timestamp with an explicit UTC offset.
- expected_state is online or planned_off.
- observed_runtime_issues lists saved runtime issues, such as a missing process or listener. An empty list means the saved runtime is online.
- tasks lists task records for that program profile. Each record has a name and can include enabled, state, and last_run.

The original rule recognizes enabled, running tasks whose names include restart, rollover, or wipe. The difference between observation and task start must be between minus one minute and 45 minutes, inclusive. Task timestamps without an offset are treated as UTC. A missing or malformed task timestamp provides no maintenance evidence. A planned-off state takes precedence.

The CLI prints a JSON report and leaves the source file untouched. The classification uses the supplied observation time and evidence. It returns 0 for a classified snapshot and 2 for invalid or unreadable input. Reports include supplied task names and issue text.

Qualification preserves the original maintenance test and runs six copied-CLI check groups, including both clock boundaries and the values just outside them. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/scheduled-maintenance-classifier-v0.1.0/VALIDATION.json).
