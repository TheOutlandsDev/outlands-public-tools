# Fictional profile walkthrough

`generate.py` creates four tiny text files under two source folders, `orchard`
and `meadow`, in one new destination under an existing private parent. Existing
destinations are refused. No game, mod implementation, real profile or proprietary
configuration is bundled. The payloads explicitly identify themselves as fictional.

Follow the complete Windows/Linux command sequences in [README](../README.md).
The engine workspace must be a different new path from the generated source.
Normal expectations:

| Step | Expected observation |
| --- | --- |
| Generator | Two profiles and four files created; exit0. |
| Initialize | New private workspace, no active profile; exit0. |
| Import orchard/meadow | Each profile contains two verified files and a config directory; originals unchanged. |
| Plan orchard | Read-only allowed activation plan; no active tree created. |
| Activate orchard | Managed `active` copy matches the orchard profile. |
| Switch meadow | Managed `active` matches meadow; the previous orchard active copy is retained in operation history. |
| Deactivate | No active profile; meadow active copy is retained. |
| Reactivate orchard | A fresh verified orchard active copy; no game installation is modified. |

Use a fresh workspace and new fixture destination for repeat acceptance runs.
Reusing an imported profile ID or an existing output destination is a refusal,
not permission to replace existing content. The example is separate from the
unittest counts and does not certify game behavior or metadata anonymity.

To explore drift using only disposable data, add a small invented unexpected
file inside the generated workspace's active tree after a successful activation.
Status/plan or mutation checks should require review. Preserve that demonstration
workspace for inspection; do not bypass guards or use this experiment on actual
game files. Crash/recovery cases are provided as generated tests using internal
Python fault injection, not a public environment flag that could disrupt real data.
