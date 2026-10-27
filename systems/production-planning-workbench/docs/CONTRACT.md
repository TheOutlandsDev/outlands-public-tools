# Neutral project contract

The complete invented [project](../examples/sample-project.json) is the starting
format. It contains no original operating policy or data. The
[order revision](../examples/sample-order-revision.json) adds a fictional increase.

## Sections

| Section | Meaning |
| --- | --- |
| `format`, `project_id`, `title`, `planning_date` | Explicit instance scenario identity and fixed planning date; no machine/user metadata is discovered. |
| `planning_configuration` | Declared product mappings, seven stages, timing, risk thresholds, start allowance and caller-asserted provenance. The `DECLARED_PLAN_ONLY` status does not mean independent approval. |
| `demand_configuration` | Product identity, gross-demand lot size, prefix and lead-time rules for the retained versioned-order reducer. No external database/production authority is represented. |
| `lot_policies` | Explicit lot-size/factor rules and observed historical identities for bounded sequence proposals; prefixes and sizes must agree across contracts. |
| `order_history` | Append-only order states with stable identity, increasing row versions, caller-supplied source fingerprint, quantity, declared accepted shipping quantity, due date and cancellation flag. |
| `wip` | Caller-declared available units, product identity, lot, mapped operation and stage 1–7. No yield/import normalization is inferred. |
| `handoffs` | Optional current-order-version dock declarations allocating stage-7 stock, with a dock date and explicit per-lot clearance assertions. |

Inputs use strict JSON: no duplicate keys, invalid UTF-8, non-finite numbers,
extra fields or coercion from booleans/strings/floats to integer quantities.
Public boundary validation uses Pydantic's strict JSON parser after independent
JSON checks; dates and Decimal values use their JSON representations.

At most 100 projects and 200 revisions per project, 16 products, 1,000 historical
order states, 200 distinct order IDs, 500 WIP rows and 200 handoffs are accepted.
Each handoff has at most 100 lots. Each input/report buffer is at most 4 MiB;
JSON depth is at most 64. Stores are capped at 64 MiB by the native I/O guard.
There are at most 5,000 saved local action events. Oversize plans or more than
100 proposed lots per product are refused; nothing is silently truncated into
a successful plan. Nested model collection bounds also apply.

The inherited engine's operation-to-stage map must agree with every WIP row.
Stages 1–6 are allocated; stage 7 is excluded from that engine. Only explicitly
assigned stage-7 dock stock reduces open planning demand. Unassigned stage-7
stock is deliberately not automatically assigned; complete the dock declarations
before relying on uncovered-demand recommendations. Handoff stock is conserved
across orders, cannot exceed an order's remaining demand and must reference its
current version. A date/clearance assertion is not independent shipping evidence.

The priority ranking horizon is bounded to six future shipments so calculated
sort values fit the original output range. Mapping days are at most 365 and each
product has at most 128 mapped operations. Effective dates after the planning
date, unsupported products and conflicting identities/policies are refused.

## Operator command example

Create a private command using identities from your current `plan` result:

```json
{
  "project_id": "sample-workshop",
  "revision_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "action_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "actor": "sample_reviewer",
  "change": {"command": "FLAG_EXCEPTION", "expected_version": 0,
             "note": "Fictional inspection needed", "exception_code": "SAMPLE_CHECK"}
}
```

The hashes above are invented placeholders. `ACKNOWLEDGE` requires OPEN;
`FLAG_EXCEPTION` refuses an already open exception; `RESOLVE_EXCEPTION` requires
EXCEPTION and a note; `ADD_NOTE` preserves the current status and exception code.
Notes are at most 1,000 characters. Stale versions/revisions are refused.
Reviewer aliases and local history are assertions, not identity verification.
