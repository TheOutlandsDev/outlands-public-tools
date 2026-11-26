# Offline Scheduler Recovery Evidence Classifier

Extract the source ZIP and open a terminal in the extracted folder. The release was qualified on Windows and Ubuntu x64 with Python **3.12.16** and **3.15.2**. It uses only Python's standard library.

## Review the fictional recovery record

```
python scheduler_recovery_evidence.py --input examples/recovery.json
```

The example reports automation status advisory. The failed logon-recovery task stays marked unhealthy in the task list. Its warning becomes an advisory because the saved runtime is online, readiness is healthy, and the profile has a newer healthy task record.

## Input and output

Use a UTF-8 JSON file of at most 2,000,000 bytes. Include four fields.

- runtime_status is online, down, maintenance, or planned_off.
- state_healthy is true, false, or null. An advisory requires true.
- expected_tasks lists the task names belonging to one program profile. Matching is case-insensitive.
- tasks lists the observed task objects. These include a name, and can include enabled, state, last_result, last_run, and next_run. Omit a task from this list when there is no record for it.

The original health rule requires an enabled task and accepts a running state or a recognized result code. A superseding run must have a strictly later timestamp. UTC offsets are respected. A timestamp without an offset is interpreted as UTC, and a missing or malformed timestamp provides no ordering evidence. Task names outside the expected profile are ignored. The JSON report covers scheduler evidence and the supplied states, so it can complement a separate service or endpoint health report.

The CLI prints JSON to standard output and leaves the input untouched. It returns 0 for a classified snapshot and 2 for invalid or unreadable input. Qualification runs the original recovery case and six copied-CLI check groups using fictional records. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/scheduler-recovery-evidence-classifier-v0.1.0/VALIDATION.json).
