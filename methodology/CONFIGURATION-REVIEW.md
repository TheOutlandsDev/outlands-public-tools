# Configuration metadata, overlays, pair rules and migration review

These offline tools review supplied metadata and fingerprints. They do not decode
values, generate settings, inspect software, open adapters or execute migrations.

| Term | Plain-language meaning | Exact meaning here |
| --- | --- | --- |
| Metadata contract | A selected description of configuration fields | Exactly id, revision and fields. Each field has id, type, required, default_sha256 and constraint_sha256. Types are boolean, integer or string; fingerprints are opaque, not executable schemas or values. |
| Default or constraint fingerprint | A supplied reference to information kept elsewhere | default_sha256 is null or lowercase SHA-256; constraint_sha256 is SHA-256. No default insertion, value validation, range interpretation or constraint widening/narrowing is inferred. |
| Layer | One explicitly ordered set of proposed changes | ID/revision, ordinal and full normalized contract pin. Layer ordinals are unique and contiguous from 1; no environment expansion, includes or implicit precedence. |
| Overlay | Replay of selected metadata changes in layer order | Start empty; order changes by layer ordinal then key. Set needs the field's declared type and a value fingerprint. Replacing a present key needs allow_override true. Delete has null type/fingerprint and cannot permit override. |
| Required final field | A required key must remain after all layers | A delete followed by a later explicit set is allowed. Optional keys may remain absent. A declared default does not satisfy a missing required key. |
| Effective configuration fingerprint | A binding to the final metadata proposal | SHA-256 of contract_sha256 and sorted present key/type/value-fingerprint rows. Provenance is reported separately; this is not a hash of an actual settings file and does not validate underlying values. |
| Contract difference | A descriptive comparison of selected field metadata | Sorted field IDs with added, removed, changed or unchanged state; changed attributes are type, required, default_sha256 or constraint_sha256. Any field difference requires review. Header-only changes may PASS; no breaking-change inference. |
| Contract identity conflict | One selected identity has incompatible definitions | Equal id/revision with different normalized definitions withholds comparison assessment and scope pins. Migration cohorts select one revision per contract ID; use distinct IDs for separately selected snapshots. |
| Component version | A caller-supplied symbolic label | No semantic-version ordering, version ranges, discovery or installation is performed. Each component also declares a revision and opaque contract pin. |
| Requested pair and rule | One explicit component relationship and its claimed decision | Symmetric exact component snapshots. Rules declare allowed true or false. Only requested pairs are assessed: true is supported, false unsupported, missing rule unlisted. Supported is a declaration, not runtime compatibility. |
| Migration path | One explicitly supplied sequence of contract references | Exact source/target selectors and ordered steps binding from/to snapshots, opaque adapter hashes and symbolic required-check IDs. Continuity, unique contiguous ordinals and no repeated contract ID/cycle are required. No route search is performed. |
| No-op or short path | An unchanged proposal, or a chain that misses its target | Empty steps can PASS when source equals target. A structurally valid chain ending short retains target_reached false with REVIEW_REQUIRED. No adapter or required check is run in either case. |
| Snapshot and cohort pins | Fingerprints of normalized selected declarations | Sorted-key compact escaped ASCII JSON plus LF; field/cohort rows sorted by ID, set-like check IDs sorted, pair endpoints normalized. Raw input pin covers exact bytes. Hashes do not establish authenticity or privacy. |
| Duplicate, conflict and slot ambiguity | Identical repeats versus incompatible or competing claims | Identical normalized IDs count once plus duplicate_rows. Conflicting identity groups exclude every member. Different IDs claiming one layer ordinal, layer/key pair, component pair or step ordinal are ambiguous, even with equal decisions. |
| Qualified scope | The complete selected declaration scope has no findings | qualified_scope_sha256 exists only with no issues. Structural findings withhold assessment and scope pins; logical findings retain diagnostic assessment/pins but no qualified scope. Overlay logical findings also withhold all effective fields and their fingerprint. |
| PASS and REVIEW_REQUIRED | Selected rules were met, or findings need interpretation | CLI exits 0 and 1. PASS does not establish valid actual settings, runtime compatibility, adapter bytes, completed checks, safe migration or authority. Logical review results are not execution permits. |
| Fixed refusal | The requested input cannot be assessed | CLI exit 2 for parser, outer-shape, selector or scope bounds. Library operations raise their package's toolkit.Rejected exception. No partial/truncated success is substituted. |
| Independent package | One tool can be installed and called alone | Its own versioned MIT wheel, CLI, embedded fictional demo and check(raw_json_bytes) API. The collection pins exact versions of all four. |

## Apply the method

1. Select the contract and layer revisions explicitly. Review replacements and
   final required-key coverage. Keep raw values elsewhere; an effective fingerprint
   is a metadata proposal, not generated settings or proof of value correctness.
2. Compare contract metadata separately. Bind the overlay contract to the exact
   baseline/candidate selected for comparison. Header changes and field changes
   have different meanings; opaque fingerprints reveal no semantic constraint rules.
3. Select components, exact pair rules and explicit requested pairs. Bind full
   component snapshots, including versions. Validate all supplied rule references;
   do not treat unrequested combinations or missing rules as supported.
4. Check the one supplied migration chain against exact contract pins. Preserve
   gaps, cycles, stale references, short paths and check IDs. A declared adapter
   fingerprint is not verified bytes, and naming required checks does not run them.

The [installed exercise](../integrations/configuration-review/exercise.py) connects
all four tools with shared fictional contract pins. It demonstrates explicit
override, delete/restore, absent defaults, identity conflicts, symmetric duplicate
pairs, unlisted/unsupported pairs, stale versions, short/no-op/gapped/cyclic paths
and the unverified adapter boundary. The [component guide](../integrations/configuration-review/components.json)
provides exact APIs, formats, examples, result fields and limits for people and AI.

Each identity cohort has at most 1,000 rows; contracts have at most 128 fields.
Migration scope is additionally bounded to 4,096 selected fields and 4,096 check
references. IDs match `[a-z][a-z0-9_-]{0,47}`, revisions are 1..1,000,000 and check
sets contain 0..32 IDs. Strict JSON input is at most 4 MiB; source guides define
parser, output and native Windows/POSIX I/O limits. Actual settings, profiles,
constraints, paths, inventories, adapters, journals and reports stay private.
Fingerprints can disclose low-entropy information; these tools are not sanitizers.
