# Safety and privacy boundaries

Original source programs, operational source mappings, customer schemas, corpora,
conversation archives, model assets, identities, endpoints, credentials and existing
databases are not included. Examples are newly invented. Inputs are explicitly
selected inside a fresh private instance; no drive scan or original importer runs.

All instance content is private, including normalized values, conflicting variants,
paths, source hashes, actor/reason assertions, row locations, SQLite stores, plans,
reports and histories. Row validation is not anonymization or secret detection.
Human review assertions do not clear rights, verify factual accuracy or authorize
public sharing. Display CSV escaping is limited; JSONL is the authoritative export.

Windows handle/reparse/link checks and POSIX no-follow/nonblocking/identity checks
reuse unchanged reviewed first-party public helpers. New outputs are exclusive,
existing files/stores are never replaced, and private instances are refused inside
the source/Git tree. Trusted parent directories, quiescent input intent and no
hostile concurrent filesystem editor are assumed. Repeated source/hash checks do
not create an atomic snapshot or defeat an attacker replacing objects between
checks. Mapped filesystem behavior follows the chosen instance configuration.

Each attempt is journaled before output writes. Only a verified final marker plus
completed journal registration makes an artifact available normally. An exception
retains partial files; a killed/interrupted process leaves a pending job. Explicit
stopped recovery marks it interrupted, without replay, deletion or adoption. A
terminal event whose response was lost may already be committed: inspect history.
Fresh attempts use new IDs. Exact successful fingerprints cannot be repeated in
the same index; changed selectors/contracts/bytes or another index are different
contexts, not globally detected semantic duplicates.

The browser uses a per-process token, strict loopback Host checks, allowed same-site
Origin checks, bounded bodies, no-store responses, no CORS, text-only DOM rendering
and no automatic write retry. It is a trusted single-operator local UI, not an
authenticated multiuser service. Do not expose it remotely or share its token/page.
No source or imported record is executed. No model, email, remote database, archive
extraction, scheduler, deletion, arbitrary SQL or host-control endpoint is present.

Metadata index backups exclude preview/store bytes. Preserve the complete instance
separately when needed. There is no automatic instance restore or corruption repair.
Finite per-operation and journal caps do not bound all disk usage. Production,
long-term retention, hardware/power-loss recovery, encryption and signed attestation
are unverified. Python/SQLite, browser activity and the OS may have external side
effects beyond this app's logic; zero external activity is not guaranteed.
