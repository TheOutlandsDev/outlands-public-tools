---
name: review-change
description: Review a code diff for concrete defects, regressions, and unsupported validation claims.
---

Use a fresh review session when independent judgment is requested. Read the diff, related implementation, contracts, and relevant tests. For each supported defect, give its location, the input or sequence that triggers it, impact, and a useful check. Prefer correctness and missing behavioral coverage over stylistic preferences. Separate the checks actually executed from supplied transcripts. Return a clear no-findings result when evidence supports it, with remaining limits.
