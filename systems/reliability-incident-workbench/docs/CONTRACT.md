# Supplied-observation contract

An import object has exactly `actor`, `reason`, `case`, `snapshots`. Creation omits
`snapshots`. Case fields are `case_id`, `title`, `policy`, `services`, `maintenance`.
Actor and label values are assertions; they are not discovered or authenticated.

Policy fields are integer `maximum_age_seconds` (1-3600), `maximum_gap_seconds`
(1-86400), and `clean_samples` (1-10). Services declare unique `id`, private `label`,
`expected_state` (`online` or `planned_off`) and one to four unique required signal
IDs. IDs are lowercase ASCII tokens starting with a letter, at most 40 characters;
digits, underscores and hyphens are allowed. Windows device names are rejected on
both platforms. IDs are not paths, addresses or executable names.

Maintenance fields are unique `id`, declared `service_id`, UTC `start`/`end` and
`reason`. Windows are half-open `[start, end)`, positive, at most 24 hours and cannot
overlap for the same service. Configuration never changes inside one case history.
Use a separately named case to review alternate assumptions.

Snapshots have unique `id`, `at`, `services`. They must be strictly chronological.
UTC values have exact form `2030-01-01T00:00:00Z`, whole seconds, years 2000-2099.
No ambient clock or original host timestamps are consulted. Service rows contain
`service_id`, `signals`; signal rows contain `id`, `state`, `observed_at`, `note`.
States are `healthy`, `degraded`, `down`, `unknown`. Omitted service/signal rows are
unknown, not healthy. Undeclared or duplicate rows fail. Observations cannot be in
the future relative to their enclosing snapshot or move backwards for that signal.
The same observation timestamp may repeat only with identical state/note bytes.
Changed notes require a new observation timestamp.

An `act` request contains `case_id`, `expected_sha256`, `command`. Commands contain
`operation`, `actor`, `reason`, `data`. `ingest` data has only `snapshots`; the whole
batch is validated before one revision is appended. Duplicate samples, stale hashes,
bad later rows and size/count limits fail without partially accepting observations.
There is no automatic deduplication, sorting, backfill or write replay.

`acknowledge` data has `incident_id`, `expected_episode`, `expected_escalations`,
`actor`, `reason`. Actor/reason must match the enclosing command. An existing
unresolved incident and exact episode/escalation counters are required. The stored
assertion binds the current snapshot count. Acknowledgements remain in history;
escalation or reopening makes earlier ones inapplicable.

All revisions include the event, resulting document, parent hash and version in a
canonical JSON hash. Reads replay commands and compare canonical typed JSON, so
Boolean/integer substitutions cannot pass through Python's loose value equality.
Hashes prove byte relationships within the retained history; they are not signatures
or trusted authorization. Rewriting the entire history remains possible to a local
attacker with write access.

Exports require exact current hash, actor/reason and Boolean `quality`, `privacy`,
`rights`, `context`, all true. Those are private review assertions and never a public
redistribution authorization. Reports preserve unknown coverage and supplied facts;
they do not verify a service, port, process, player count or actual operating state.
