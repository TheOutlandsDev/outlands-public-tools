# Server Maintenance Planner

`maintenance.py` is an offline Python 3.12+ standard-library planner for generic server lifecycle decisions. It reads bounded caller-supplied JSON or calculates recurring calendar dates. It does not control a service, process, game, network endpoint, RCON interface, scheduler or machine.

## Lifecycle plan

Prepare a small JSON file with these exact fields:

```json
{
  "action": "restart",
  "state": "running",
  "players": 0,
  "observation_age_seconds": 30,
  "maximum_age_seconds": 300,
  "cooldown_remaining_seconds": 0,
  "previous_attempt": "completed",
  "target_verified": true,
  "backup_verified": true
}
```

Then run:

```text
python tools/server-maintenance/maintenance.py plan --input PRIVATE_PLAN.json
```

The input facts are supplied by the operator. The planner checks their shape, freshness and consistency, then returns a conservative status and ordered checklist. It does not independently verify the target, backup, player count, prior attempt, or observation source. `execution_performed` is always false.

Supported actions are `start`, `stop`, `restart`, `update` and `backup`; service state is `running`, `stopped` or `unknown`. Unknown/stale observations, present players, a pending cooldown, an incomplete prior attempt, or unverified prerequisites block or defer a plan. A plan is a checklist only; it is not a runbook for a particular product.

## Readiness observations

```text
python tools/server-maintenance/maintenance.py readiness --input PRIVATE_READINESS.json
```

The JSON object must contain boolean fields `target_verified`, `new_instance`, `fresh_log_markers` and `probe_succeeded`. `OBSERVATIONS_COMPLETE` means the caller supplied `true` for all four fields; this tool does not collect the observations or probe a service.

## Calendar window

```text
python tools/server-maintenance/maintenance.py calendar --year 2026 --month 11 --weekday 0 --offset-days 7
```

Weekdays use Monday `0` through Sunday `6`. The output names the first weekday and a non-overlapping follow-up date. Time of day and time zone remain operator-selected; this command does not register or run a schedule.

Input files are limited to 64 KiB. JSON duplicate keys and non-standard numeric constants are rejected. Errors use fixed codes and omit the input path. Keep real operational plans private if their filenames or contents identify infrastructure or people.

See [input checks and platform limits](INPUT-SAFETY.md) and the
[current input review](../../docs/BATCH-32-SERVER-MAINTENANCE-INPUT.md).
Windows requires the adjacent `maintenance_windows.py`; POSIX loads only the
main module. Planning rules and JSON parsing are preserved; Windows path
restrictions are stricter and handled Windows interruption returns exit 130.

See [Batch 7 review](../../docs/BATCH-7-REVIEW.md) for original provenance. MIT licensed; see [licensing](../../LICENSING.md).
