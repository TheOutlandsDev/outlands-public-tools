# Validation and interpretation limits

worker-queue-checks qualifies Python 3.12/3.13 on Windows and Ubuntu. Required native
fixtures cover read/hash, fresh write/readback, hardlink-input refusal, linked-parent
refusal, changed-input detection and overwrite refusal. Only opposite-platform methods
may skip; local volume skips are not native proof.

Known-answer/adversarial tests cover exact handler/interface pins, required metadata
missingness, set-like normalization, explicit same-kind handler selection and opaque
payload fingerprints; expiry-boundary takeover, overlap, strict increasing token
declarations, rejected high tokens, renewal extension, wrong owner, release truncation,
future/missing histories, gaps/reversed times and exact job snapshots; missing/future/
late acknowledgements, requeues/dead letters, active unresolved deliveries, delivery
after terminal outcomes, explicit redelivery after expiry, changed worker/token and
alias acknowledgement slots; exact result/commit bindings, missing/aliased commits,
timely result with expired commit, stale old results, source-contract mismatches,
future claims and result aliases. Every identity list checks complete conflict,
duplicate and rejected-row accounting. Shared strict JSON/I/O tests preserve source
protection, fixed errors and no-overwrite behavior.

Actual collection acceptance copies each complete directory independently, verifies
source pins and runs its CLI, creates fresh reports, refuses overwrite/source output,
checks raw-input pins/unchanged inputs/fixed errors and verifies no action artifacts.
Connected invented HVAC jobs bind the same item/lease/delivery cohorts across four
CLIs. A former owner's late acknowledgement/result remains a finding even alongside
a consistent current claim. A separate game-build job contains no game assets/code.
Two explicit fictional adapters call existing public Retry Budget Checker and
Idempotency Ledger Reconciler, including too-early retry and conflicting terminal
result counterexamples. Those engines are not duplicated or imported into these tools.

These synthetic checks do not establish genuine queue delivery, complete histories,
worker authentication, payload correctness, real lease enforcement, exactly-once
execution, real artifact bytes/commits, production suitability, privacy or rights.
Original implementations, schemas, policies, records, customer/user data, paths,
credentials, endpoints and deployment details were not consulted or selected.
No queue, worker, clock, handler, payload, artifact or database is accessed.
