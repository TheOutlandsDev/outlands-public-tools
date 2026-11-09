---
name: fix-bug
description: Diagnose and fix a reported software failure with a reproduction and a regression check.
---

Find the smallest existing command or test that reproduces the reported failure. Record its actual outcome. Trace the failing behavior through the implementation and inspect nearby edge cases. Make a coherent fix and a meaningful regression test when needed. Run the relevant checks, inspect the diff, and report the before/after evidence. If reproduction or a dependency is unavailable, state that boundary and avoid claiming the issue is verified fixed.
