# Offline Game NPC Behavior Policy Validator

Use Python **3.12.16** or **3.15.2** on Windows or Ubuntu x64. Extract the source ZIP. The validator uses only Python's standard library.

## Check three fictional policies

Run these commands from the extracted folder.

```
python npc_behavior_policy_validator.py rust --input examples/balanced.json
python npc_behavior_policy_validator.py dayz --input examples/warning.json
python npc_behavior_policy_validator.py rust --input examples/invalid.json
```

The balanced policy passes with no warnings. The DayZ example passes with three warnings about fast reactions, low aim error, and a high-aggression policy with a very low retreat threshold. The last example fails the reaction-time and perception-range checks. Reports go to standard output. The CLI exits with 0 for valid policies, including policies with warnings, 1 for invalid policies with a report, and 2 for input errors.

## Input and output

The profile is one of rust, dayz, main_spt, modern_warfare, or zomboid. Pass a saved UTF-8 JSON object with a policy object containing any subset of the settings below. An omitted policy is treated as an empty policy. Bounds include both endpoints. The report normalizes supported finite numbers, including numeric strings.

| Setting | Range |
| --- | --- |
| reaction_ms | 150–2,000 |
| aim_error_deg | 0.5–30 |
| aggressiveness | 0–1 |
| coordination | 0–1 |
| retreat_health_percent | 1–100 |
| pursuit_seconds | 0–300 |
| decision_interval_ms | 100–5,000 |
| perception_range_m | 5–500 |

Unknown policy fields and out-of-range or nonnumeric values produce errors. Inputs beyond 2,000,000 bytes, duplicate keys, malformed JSON, and top-level execution fields are refused. The validator reads the saved policy and emits a report. Passing the check leaves the offline simulation, game-specific review, and approval requirements in the report.

The four qualification profiles run the original policy test and six CLI check groups from the extracted source ZIP. [Validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/game-npc-behavior-policy-validator-v0.1.0/VALIDATION.json).
