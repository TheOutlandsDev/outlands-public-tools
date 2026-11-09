---
name: understand-repo
description: Map an unfamiliar repository and identify its entry points, dependencies, and build/test commands before changing code.
---

Read AGENTS.md, the main README, build manifests, relevant CI, and the source paths related to the user's task. Trace one concrete entry point through its implementation and tests. Return a compact map with file references, the declared runtimes, candidate verification commands, and unresolved assumptions. Do not run installation or change files merely to produce the map.
