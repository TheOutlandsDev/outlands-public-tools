# Cache, retry and operation-record terms

Use these meanings with the [general terms](TERMS.md) and the tool's exact schema.
All values in examples are invented; actual job records and payloads stay private.

| Term | Plain meaning | Precise meaning here |
| --- | --- | --- |
| Cache | A stored result that may be reused. | These tools inspect declarations about stored results, without opening or changing a cache. |
| Namespace | A name that separates one key scheme from another. | An explicit ID in a cache contract; it is included in the contract hash. A cache-result key and an operation key have separately declared meanings. |
| Dependency fingerprint | A reference to the exact inputs behind a result. | A dependency ID, revision and SHA-256 declaration. The tools compare these values without authenticating or opening the underlying artifact. |
| Key version | Which declared key scheme is in use. | An explicit integer in the hashed contract. It is distinct from the contract revision and dependency revision. |
| Freshness | Whether the supplied result meets age and invalidation rules. | Compare explicit creation, lifetime, matching invalidations and caller-supplied as-of values. A fresh assessment permits manual read review, not cache access. |
| Ordinal | A number representing a position on a caller-defined timeline. | Nonnegative integer values in one explicit common convention. Tools do not read a clock or guess units, dates or time zones. |
| Expiry | The point after which a result is too old under the policy. | expires_at = created_at + lifetime; equality at as_of is expired. A zero lifetime expires immediately. |
| Invalidation | A declaration that a dependency snapshot should no longer be used. | Match the exact dependency ID, revision and hash. A matching invalidation at or before as_of remains effective for that snapshot. |
| Retry budget | A cap on attempts for a selected operation. | maximum_attempts includes the first attempt. A declaration of remaining budget does not authorize or reserve another attempt. |
| Backoff | A declared delay before another attempt. | After failed attempt k, require min(maximum_delay, base_delay * 2**(k-1)). There is no jitter, sleep or dispatch. |
| Idempotency | Repeating a request is intended to have the same effect as making it once. | The ledger checker only reconciles supplied key, payload, state and result claims. Consistent records do not prove exactly-once execution or enforce duplicate prevention. |
| Terminal claim | A record says an operation finished. | A succeeded or failed state with a result pin. One unambiguous failed claim can PASS consistency while still describing failure. |
| Unknown outcome | The supplied record does not establish an outcome. | It remains unresolved. It is not silently changed to failure, success or permission to retry. |

`PASS` means consistency within the stated input rules. A fresh cache declaration,
a due retry history and an unambiguous terminal claim each answer different
questions. Read the reported scope and eligibility fields. `REVIEW_REQUIRED`
retains valid diagnostics where possible; invalid scope can withhold assessment
and qualified pins. CLI exits are 0 for pass, 1 for review and 2 for fixed refusal.
