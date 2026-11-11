# Documentation Check

Check a bounded local Markdown/JSON tree without fetching links or executing
source. The Python CLI checks its supported Markdown link subset and JSON
syntax, returning JSON on standard output. It writes no selected files, reports
or manifests; ordinary reads may affect operating-system access metadata.

Download the initial **0.1.0 standalone source ZIP** from the
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/documentation-check-v0.1.0)
and extract it into a fresh source directory. Keep **`docs_check.py` and
`docs_windows.py` adjacent**. Use Python **3.12–3.15**; qualification selects
3.15.2 for that minor. There are no third-party packages, pip installs, network,
model or account requirements. The source ZIP contains no interpreter, binary,
real document tree, report, original private helper or raw diagnostic log.

```text
python -B docs_check.py --root ABSOLUTE_TRUSTED_DOCUMENTATION_DIRECTORY
```

Choose a stable ordinary local tree and trusted unchanged parents. Read
[USAGE.md](USAGE.md) for Windows/Ubuntu commands and a fictional good/bad-tree
walkthrough that records real CLI exits/JSON and checks input bytes are unchanged.
Use an external [private workspace](docs/PRIVATE-WORKSPACE.md) for generated
fixtures and any explicit shell captures. User-owned Python/venvs do not
inherently require administrator access; follow device policy without bypasses.

## What the result covers

- Common inline/image links and reference definitions, with limited fence and
  simple inline-code handling. Local paths must remain within the selected
  root, and missing or observed linked/reparse targets produce findings.
- HTTP, HTTPS and mail links are skipped without fetching. Other link schemes
  fail. Pure fragment links are skipped; anchors are not validated.
- JSON syntax rejects nonstandard NaN/infinity constants. Existing default
  duplicate-key behavior remains; this is not a duplicate-key or schema checker.
  UTF-8 BOM handling and universal newline conversion are retained.
- Only selected Markdown/JSON is checked. Root Git metadata, hidden
  subdirectories, private/runtime locations, caches and dependency trees are
  excluded according to the preserved rules. Excluded entries still consume
  the encountered-entry budget.
- Bounds are 10,000 encountered entries and 2 MiB per selected file. Collection
  is bounded before sorting, and actual reads check identity/size. These are
  not total-byte, CPU, elapsed-time, result-size or process-memory quotas.

The parser does not implement full CommonMark, resolve reference uses against
all definitions, validate anchors, fetch external sites, validate JSON schemas
or attest to excluded material. A link target's existence does not validate its
contents or application behavior. Read [FILESYSTEM.md](docs/FILESYSTEM.md) for
the exact preserved grammar, native behavior and historical evidence.

| Exit | JSON status | Meaning |
| --- | --- | --- |
| `0` | `PASS` | Documented selected checks passed; help also exits zero. |
| `1` | `FAIL` | Findings were produced. This is a completed finding result. |
| `2` | `ERROR` | Fixed argument/root/input-output failure; no complete check claimed. |
| `130` | `ERROR` | Handled Windows interruption (`DOCUMENTATION_CHECK_INTERRUPTED`). |

Some selected-file read/size/type failures are findings and therefore exit 1;
root/directory/argument failures can return exit 2. POSIX interruption behavior
is preserved. There is no `--output` option: shell redirection/capture is an
explicit separate user action and can overwrite a destination if used carelessly.

## Native files, privacy and evidence

Windows uses native path/name/handle/identity checks, metadata-only local-target
access and observed link/reparse/short-name rejection. Keep fully spelled local
paths. POSIX retains containment/link checks, available no-follow/nonblocking
flags and bounded descriptor reads. Source hard links cover unnamed data only;
ADS, ACLs, ownership and full metadata are outside scope. The preserved platform
contracts differ in some target-type and interruption behavior.

Use trusted quiescent parents and stop writers. Sampled checks have race
windows; they are not atomic snapshots, a hostile-filesystem sandbox, universal
I/O timeouts, remote/live-provider acceptance or power-loss protection. PASS
means documentation hygiene, not security, confidentiality, source rights or
application acceptance.

JSON retains **relative filenames and line numbers**, which can identify private
work. It is not redacted or anonymous. Shell arguments/history and captures can
retain information too. Keep actual reports/docs/mappings private and use
newly authored fictional public reproductions.

Eight fresh extracted-ZIP Windows/Ubuntu Python lanes use new venvs without
pip or distributions, the original documentation regressions/native safety
cases and copied-runtime CLI fixtures. Actual versions/counts/skips belong to
release `VALIDATION.json`; planned coverage is not a passing result. Read
[qualification](docs/QUALIFICATION.md) and separate historical
[filesystem evidence](docs/FILESYSTEM.md).

Selected original source is [MIT licensed](LICENSE), with retained notices and
AI assistance; no exclusive-authorship claim is made. Read
[provenance](docs/PROVENANCE.md),
[collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md)
and the [earlier review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-28-DOCUMENTATION-CHECK-HARDENING.md).
[Report an issue](https://github.com/TheOutlandsDev/outlands-public-tools/issues)
with minimal fictional source, OS/Python version, expected behavior and actual
exit/status. Do not attach real documents, personal paths or unreviewed reports.
