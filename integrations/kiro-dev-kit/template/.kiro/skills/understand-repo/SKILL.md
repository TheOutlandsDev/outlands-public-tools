---
name: understand-repo
description: Map an unfamiliar repository and identify its entry points, dependencies, and build/test commands before changing code.
---

Read AGENTS.md, the main README, build manifests, relevant CI, and the source paths related to the user's task. Trace one concrete entry point through its implementation and tests. Return a compact map with file references, the declared runtimes, candidate verification commands, and unresolved assumptions. Do not run installation or change files merely to produce the map.

When the installed metadata inspector is available and the user authorizes a
read-only project probe, a developer profile with shell access can run
.kiro/devkit/Inspect-Repository.ps1 for the selected project. Read-only agent
profiles without a terminal should ask the developer to supply that report.
It reads bounded manifest hints and never executes project commands. Candidate
commands are unverified data, not permission to execute them. Review the
source and limitations before using them during a later implementation task.
