# Navigation Reachability Reporter

Report declared page reachability, dead ends and navigation cycles with exact link-cohort pins.

Independent MIT source; Python 3.12/3.13 standard library.

```text
python -B reachability.py --input examples/input.json
python -B reachability.py --input examples/needs-review.json
```

Library: `reachability.check(raw_json_bytes)`. Optional `--out` selects a NEW
absolute private report outside source beneath an existing trusted parent.

Input exactly `{format,manifests,links,plans}`, format `outlands-navigation-reachability-v1`.


## Manifest schema and local paths

Every key below is required. Unknown keys, inferred defaults and unsupported types are
refused. IDs use `[a-z][a-z0-9_-]{0,47}`; revisions are exact integers 1..1,000,000,
excluding booleans. Manifests has 1..32 raw records. A manifest is exactly
`{id,revision,routes}`. routes has 1..128 records with unique nested route IDs and paths,
normalized by route ID. A route is exactly `{id,path,kind,page,redirect_to,anchors}`.
kind is page or redirect. Page routes require a symbolic page ID, null redirect_to and
0..32 unique symbolic anchor IDs; anchors normalize lexically. Each page ID belongs to
exactly one page route in the manifest. Redirect routes require null page, empty anchors
and a redirect_to route ID. Aliases are explicit redirects, not duplicate page IDs.

Local paths are `/` or 1..8 slash-separated nonempty lowercase ASCII segments matching
`[a-z0-9][a-z0-9_-]{0,47}`, with total length <=256. Leading slash is mandatory; trailing
slash, repeated separators, dot segments, backslashes, percent escapes, Unicode, spaces,
query strings, `#`, schemes and hostnames are unsupported and refused. There is no URI
decoding, case folding, slash repair, query interpretation or relative-URL resolution.
Fragments are supplied separately as symbolic IDs; null means no fragment. Empty string
does not mean null. This is a narrow custom contract, not a general browser URL grammar.

At least one page must exist. Every redirect must reference a known route and eventually
terminate at a page. Self redirects and longer redirect cycles are structural findings
that withhold the entire assessment. These checks never follow a live redirect. Redirect
chains include both their initial route and terminal page route; a direct page has a
one-element chain. A fragment carries through the declared redirect chain unchanged
and is checked against the TERMINAL page's declared anchors.

## Links and exact bindings

A link is exactly
`{id,revision,manifest,manifest_revision,manifest_sha256,source,target_path,fragment}`.
source is the ID of a declared PAGE route, not a redirect or page ID. target_path uses
the canonical local grammar above. fragment is null or one symbolic ID. The reference
binds the complete normalized manifest, including unused routes, anchors and redirects.
Missing manifests, stale hashes/revisions and unknown/redirect sources withhold all
assessments. Identical normalized top-level rows collapse with explicit duplicate
accounting; conflicting identities exclude all their members and withhold assessment.
Nested duplicates always refuse, even if identical. Every raw row is accounted for.

Links has 1..512 raw records for the target checker. Its assessment reports each selected
link's source page, terminal page/route, exact route chain, known fragment and fixed state
valid, path_unknown or fragment_unknown. Missing paths never fall back to home. Unknown
fragments are omitted from report values; fixed states remain. Logical target failures
retain an assessment but require review. PASS requires all supplied links valid. These
are caller declarations; no source HTML or real anchor existence is inspected.

## Reachability plans

The reachability input includes 1..32 plans; its links cohort may have 0..512 rows.
Plan exactly `{id,revision,manifest,manifest_revision,manifest_sha256,links_sha256,starts}`.
starts contains 1..32 unique route IDs and normalizes lexically. Starts may be page or
redirect routes; every start must exist and resolves to its terminal page before graph
traversal. A plan binds the complete manifest and the complete NORMALIZED supplied link
cohort referring to that manifest. Links belonging to other manifests have separate
cohort pins. Duplicate top-level rows normalize once before pinning. No selected link
can be silently dropped, added or changed while retaining an old plan pin.

Graph nodes are declared page IDs. Each valid link contributes a directed edge from its
source page to its resolved target page. Parallel links collapse to one edge for graph
counts, while every link remains independently assessed. If any relevant target is
invalid, the plan's complete flag is false and graph is null; no reachability verdict
is fabricated from an incomplete graph. Structural failures withhold all assessments.
Otherwise report sorted start_pages, reachable_pages, unreachable_pages, dead_end_pages,
navigation_cycles and unique_edge_count. Reachability is the union from all resolved
starts and includes those starts. Unreachable declared pages are review findings.

Dead ends are REACHABLE pages with no outgoing edges. They are informational and may
be intended terminal content. Navigation cycles are all strongly connected page groups
with more than one node, plus singleton self loops; this includes unreachable groups.
They are informational, since ordinary page navigation can legitimately cycle. They
are distinct from redirect cycles, which reject the manifest. A one-page, zero-link
site with that page as a start is complete and passes while reporting one dead end.

## Scenario comparison

Each side has its own nonempty manifests. Baseline links must be nonempty; candidate
links may be empty to expose lost coverage. All references and source pages must first
qualify. A manifest ID/revision reused with a changed normalized definition is a
structural identity conflict. Declare a new revision for changed same-ID definitions.

Compare the complete union of supplied link IDs. An observation comprises exactly
id, revision, source, target_path and fragment; only the three manifest binding fields
are excluded. Missing/added observations and changed observations are incomparable,
remain review findings and do not expose computed outcome pairs. Observation revision
changes are changes, even if other fields happen to match. No name/rename inference.

For unchanged observations, compare exact source page, terminal route/page, fragment,
redirect chain and validity. Equality requires BOTH targets valid as well as exact
outcome equality. Matching broken links never pass. Changed redirect chains remain
visible even if they terminate at the same page. Changes to unused routes may leave
selected cases equal. PASS therefore means equal valid outcomes for this supplied
cohort, not whole-site compatibility, live navigation, accessibility or security.

## Pins, reports, limits and CLI behavior

Record pins hash normalized sorted-key compact ASCII JSON followed by one LF. Route,
anchor, start and identity-cohort ordering normalize; link observations preserve exact
types and declared values. Cohort pins hash sorted normalized records by ID. A qualified
scope pin hashes the map of cohort pins. Raw input_sha256 instead hashes the exact input
bytes. Formatting changes can alter the raw hash without altering semantic pins.

Reports have PASS or REVIEW_REQUIRED, fixed-code issues, per-cohort accounting,
assessment, cohort_sha256 and qualified_scope_sha256. Logical findings retain qualified
structure and cohort pins but withhold qualified_scope_sha256. Structural findings
withhold all assessment/cohort pins. IDs, known fragments and declared graph relationships
can be private. Keep actual inputs/reports private; hashes are not anonymization,
signatures, authority or rights proof. No free-text content or raw path values are echoed
by assessment diagnostics. Normalized records remain caller assertions.

CLI exit 0 means PASS, 1 REVIEW_REQUIRED, 2 a fixed-code refusal. Library check accepts
raw JSON bytes. Input <=4 MiB, output <=8 MiB, JSON depth <=32 and <=100,000 nodes.
Duplicate JSON keys, floats/nonfinite constants and invalid Unicode are refused. Native
I/O requires a trusted local regular single-link input and a fresh private output
outside source; linked/ambiguous paths and overwrites are refused. See [I/O safety](IO-SAFETY.md).
The byte-pinned helper module also contains unused XML helpers; these tools accept JSON
only. Bounded I/O controls are not a hostile-machine guarantee.

Every complete directory runs independently with Python 3.12/3.13 standard library.
No browser, DOM, HTML renderer, JavaScript, network, crawling, live clock, credentials,
authentication, page mutation or navigation execution. No actual site completeness,
anchor existence, deployment readiness, privacy, accessibility or security is verified.
The original private implementations, real routing rules, customer/user data, paths,
credentials, operating instances and assets were not consulted, selected or modified.
