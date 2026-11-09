# Maintenance and service review

These four tools check supplied, bounded records for a fictional equipment
service workflow. No tool opens physical equipment, reads a live meter, schedules
work, dispatches an order, moves stock or approves service.

1. **Meter history:** supplied readings, ordered events and explicit reset
   boundaries yield a cumulative usage assessment. It does not collect or
   independently verify a physical counter.
2. **Due planning:** selected time and usage intervals, an explicit as-of
   ordinal and declared meter totals yield an advisory due state. A source hash
   is a supplied reference, not a verified meter-checker receipt. The chosen
   interval's suitability and actual scheduling remain separate decisions.
3. **Order lifecycle:** selected order snapshots are checked against explicit
   revision and state events. A completed declared state is not proof of
   physical work or an operational order update.
4. **Service completion:** selected tasks, parts accounting and evidence
   declarations are reconciled against an exact order snapshot pin. It does not
   read evidence bytes, verify installed parts or authorize service approval.

The fictional examples share IDs and a repeated meter total. The completion
example uses the exact work-order snapshot pin reported by the lifecycle
example. Those relationships support a worked *supplied-record* exercise;
they do not establish an authenticated end-to-end operational chain.

`PASS` means only that the supplied data met one tool's stated rules.
`REVIEW_REQUIRED` identifies a finding or withheld conclusion. A due-state
PASS can coexist with an unverified meter source, and a completion-contract
PASS does not make physical service verified. No live application adapter or
system mapping is included.

IDs, hashes and service details can reveal private operational context. Use
fictional examples for public tests, and keep actual inputs and reports in
private, trusted storage. The package release includes generic public source
and those fictional examples only.
