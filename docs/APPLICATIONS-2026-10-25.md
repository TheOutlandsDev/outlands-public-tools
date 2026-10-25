# Application collection review — 2026-10-25

The owner chose outlands-public-tools as the shared destination for useful
original MIT applications. This change adds three application subfolders and
application-specific issue forms. Existing collection tools and their historical
validation records remain in place.

## Retained applications

Local Site Builder was copied from original MIT release commit
`4ab3827419ce7c8d97e2edce32c80ca639c44bfb` of
TheOutlandsDev/outlands-local-site-builder. Portfolio Builder was copied from
original MIT release commit `eda656d0ad13b6b5f9e12cc570c5498c3e99d920` of
TheOutlandsDev/outlands-portfolio-builder. Their exact source manifests were
checked before copying. Collection navigation/support links and manifests are
updated; code, dependency pins and third-party notices are retained. Existing
repositories were not deleted, archived, renamed or stripped of history.

Nested application workflows/forms are retained as source for self-contained
folders. GitHub activates the root collection workflows and root issue forms;
the root workflow supplies module working directories and the correct npm lock
path. No database, node_modules, PDF artifact, private site, image upload, real
evidence, password or runtime is copied into the collection.

## Job & Quote Tracker

This is a fresh generic implementation with AI assistance, based only on the
use case of keeping jobs/quotes and follow-ups. Private business prototype source,
branding, rules, records and assets were not copied. The app's own provenance
document states its MIT scope and imported-runtime boundaries. It adds persistent
SQLite storage rather than relying on the prototype's in-memory state.

The tracker has desktop and CLI modes, expected-version edits, immutable app-level
quote/decision history, status transitions, exact integer cents, new-only private
reports and consistent SQLite backup/recovery. Recorded decisions are operator
references, not verified customer authorization or signatures. This is a single
local-user utility with no roles, cloud service, invoicing or tax engine.

## Validation scope

The collection workflow runs Site Builder on Windows/Ubuntu Node 24 and both
Python apps on Windows/Ubuntu Python 3.12 and 3.13, requiring real Tk. It checks
reviewed module manifests before synthetic tests. Site Builder also runs npm's
advisory audit; Portfolio Builder checks its dated runtime advisory feed. The
tracker needs no pip dependencies. Every application keeps its detailed validation
record; source or fixture checks are not real business/runtime acceptance.

Initial local tracker run: 34 discovered cases, 33 passed and one native symlink
privilege skip; all six Tk cases passed. Committed-WAL backup, new-only recovery,
export hashes/escaping, optimistic conflicts and approval invalidation were
included. The test run used generated disposable records only. Review the current
GitHub Actions result for cross-platform outcomes.

No private business, production customer, external email, payment, real approval,
shared network database, hostile filesystem or power-loss acceptance is claimed.
Keep real inputs, private exports and backups outside this source repository.
