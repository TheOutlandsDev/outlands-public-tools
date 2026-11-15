# Qualification contract — EML/MIME Inspector 0.1.0

This record defines release gates; accepted release `VALIDATION.json` records
actual results for its reviewed commit. Required selections are not assumed
passes. The preserved [historical validation](../VALIDATION.md) remains separate.

## Exact source and interpreter identity

The source ZIP contains 28 allowlisted source files plus `SOURCE-MANIFEST.json`,
29 members. Four runtime/generator files, two original test files and three
historical records remain byte-identical. The fifth runtime file,
`native_windows.py`, has one explicitly approved `exclusive_write` safeguard fix:
a dangling/reparse output leaf must be refused without creating its missing
target. Exact baseline/current file hashes and the single-function exception
are recorded; it is not represented as unchanged source. No Python binary, real message/mailbox,
attachment, generated report, environment, raw log or private operational input
is bundled. Hashes/build manifest bind selected bytes, not authentic origin,
input rights, message authenticity or safe content.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 using the
20261110 standalone archive recipe on Windows/Ubuntu. Preparation verifies archive
SHA-256, actual version/executable hash and a fresh no-pip environment with zero
installed Python distributions. No global/admin install, runtime Python package,
GUI or independent reproducible-Python claim is made.

## Preserved originals and copied-runtime CLI checks

Eight lanes select 52 unchanged originals (30 MIME and 22 buffer/native-boundary
methods) plus 30 copied-runtime CLI methods: 82 per lane, 656 total (416 original,
240 copied). Original metrics are 51 assertion call sites: 50 within tests and one
within four helpers. Runtime definition counts remain fifty non-example plus two
generator definitions: forty-nine non-example definitions and both generator
definitions remain unchanged, with the one native output function change
explicitly attested. All original methods/helper bodies remain unchanged.
Assertion sites differ from execution selections.

Passes/skips/failures/errors remain separate. Exact opposite-platform skips bind
selected unique IDs; native hardlink and supported Windows junction fixtures are
mandatory rather than assumed privilege skips. Unsupported required primitives
fail closed. Native setup/negative controls remain separate from the 82 release
selections and do not become application passes. There is no GUI/Tk scope.

The originals have no optional privilege fixtures. One additional copied Windows
leaf-symlink case can skip locally only for its selected ID/reason and the actual
observed Windows error 1314; hosted strict lanes require it to execute. Hardlink,
Windows junction and POSIX link fixtures remain mandatory in their supported scope.

Checks cover the explicit strict MIME subset, exact default omissions/source and
decoded hashes, malformed/unsupported headers and bodies, charset/base64 rules,
multipart ordering/limits, duplicates, application bounds, fixed diagnostics,
new-file-only output, source boundaries and actual native file guards. Shared
buffer helpers' JSON/XML checks remain preserved original tests; they do not
turn this EML CLI into an XML viewer or a general mail parser.

## Exact independent fictional guide

The [guide](../USAGE.md) executes its exact block in fresh no-pip 3.15.2 using five
copied runtime files. Independent authored source bytes/decoded payloads and full
summary/file expectations import no inspector/parser matching oracle. Selected
CLI child audit events refuse remote/browser/process actions. A clearly labelled
child-only primitive fault tests retained partial output; it does not change
runtime bytes or use actual mail. Working proof is retained separately from one
committed-head rerun. Seventeen source hashes include the actual qualifier.

Sixty cases comprise 16 accepted/control observations and 44 refusals, twelve full
reports, fifteen decoded payload hashes, fifty unchanged fixtures, 2,940 repeated
input hash observations and 65 exact workspace files. The guide manifest binds 64
payload files, including the five-byte retained unconfirmed output. No refused
message emits a partial MIME summary or creates its requested report. Native
refusal-code differences are explicitly expected per platform.

Both scope positives, fictional EML flow and native file guards checked, are true.
All nine exclusions remain false: real mail used, mailboxes accessed, messages sent,
bodies rendered, files extracted, remote resources followed, message authenticity
verified, attachment safety verified and real delivery verified. Ordinary real
mail often falls outside this deliberately narrow accepted grammar.

## Interpretation and safety limits

PASS establishes supported subset structure and selected-byte consistency only.
Headers, bodies, names and filenames are omitted, but source/decoded hashes,
sizes/types/graph shape remain identifying. JSON escaping/omission is not
anonymization, encryption or permission to publish. HTML is data, never rendered,
sanitized or certified safe. No SPF/DKIM/signature/provider, mailbox, delivery,
malware, content-safety, mail-client compatibility or input-rights check occurs.

Reads/writes require trusted quiescent regular inputs and ordinary local parents.
Retained native handles or no-follow directory descriptors and sampled identities
are not locks against hostile actors or an atomic multi-file snapshot. The
primary stream is read; alternate private data is not enumerated/certified absent.
Parser bounds include post-parse checks and are not OS memory/CPU limits or hard
I/O deadlines. Failed/interrupted writes retain unconfirmed output; no automatic
cleanup/reuse, universal rollback or power-loss durability guarantee is made.
Windows inherits parent permissions; POSIX requests 0600 without a general ACL
confidentiality or full metadata-preservation claim.

Use the [Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
in fresh owned external workspaces. Review actual release outcomes and retained
[I/O safety](../IO-SAFETY.md)/[origins](../ORIGINS.md) before handling private data.
Public validation retains sanitized counts/versions/byte identities, excluding
real input data, machine paths, raw logs and operational records.
