# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for Python/venvs, fictional work, actual ledgers,
stdout captures and qualification receipts:

```text
source/assessment-record-checker-0.1.0/  selected source only
private/assessment-record/
  venv312/                              separate no-pip environment
  fictional_walkthrough.py              private copy of usage driver
  fictional-demo/                       new authored records only
  actual-records.json                    private ledger
  captures/                             caller-owned stdout/diagnostics
  qualification/                        extraction/environments/receipts
```

Select Python and `assessment_check.py` explicitly. `--records FILE` is required;
no default/environment ledger, target, attachment/evidence reader, database,
report writer or record update exists. The checker reads only that JSON and
prints stdout. Caller capture/redirection is separate and can overwrite its
chosen file; select new private captures deliberately.

The schema permits only neutral submission/finding/retest summaries with exact
typed references, declared integer revisions and enums. Do not strip private
schemas, invent outcomes or coerce unsupported operational records to force
acceptance. Narrative findings, people, commands, target/source identities,
timestamps, hashes, evidence/attachments and authorization documents are outside
the model and are not read or inferred.

References resolve by record kind. Retests need existing original/replacement
submissions in the same series with a strictly higher replacement revision.
All history is checked, including unselected retests. Open requires a null
selection. Pending/closure require an explicit owned valid retest on the highest
numeric declared revision in the original series, including untested submissions;
unrelated series revisions do not supersede it. Pending needs not_run; closure
needs not_observed. After ownership checks an invalid selected relationship
blocks before latest/outcome checks. A consistent own finding can coexist with
global review caused by bad unselected history. None proves actual testing,
remediation, authorization, isolation or security.

Results preserve each record's own ID, kind, status/evidence and counts, ordered
submissions then findings then retests, retaining each input list's order.
Reference IDs, series/revisions, states/outcomes, selected paths and native errors
are omitted. IDs/statuses still disclose designs. Real ledgers and captures stay
private; fixed errors do not anonymize caller logs or formatted tracebacks.
Review a separate export before sharing anything derived from actual work.

Use fully spelled canonical trusted paths and stable ordinary files. Components
are checked after absolute normalization; original leaf/parent dot/space refusal
must not be assumed. Actual fictional Windows probes on Python 3.12.7/3.15.2
accepted canonical, leaf-dot, leaf-space and parent-dot forms with exit 0;
parent-space returned 2/INPUT_PATH_INVALID, preserving input/runtime bytes.
These mixed observations establish no blanket original-suffix refusal. Ordinary
single-link files/ancestors with usable sampled
identities are required; observed links/reparse/special/multi-link inputs and
sampled changes are refused. These checks are not atomic snapshots, writer
denial or hostile-filesystem containment. Rebinding, arbitrary mount/drive
aliases, remote/cloud/virtual/live storage, blocked I/O, power loss and ACL privacy
remain outside acceptance. OS reads can use network storage without a socket/
DNS probe. Access metadata and Python caches remain separate.

The input is at most 64 KiB, each collection at most 128 and all records at most
256; revisions/tokens are bounded. These are not total CPU/RAM/JSON-depth/
deadline/storage quotas. Require full JSON and actual exit/status; interruption
or stdout failure can leave partial captures. No checker-owned output tree is
rolled back. Fictional work is retained without automatic cleanup. Requested
modes depend on OS/Python/ACL behavior and do not guarantee confidentiality.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. No pip distribution, network, account or model is
needed; Python retains separate terms. Build/qualification outputs must be new
private paths outside source with existing parents. Publish reviewed source/
sanitized actual validation only, excluding real ledgers/IDs/results, evidence,
personal paths, credentials, private source, binaries and raw logs.
See [USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
