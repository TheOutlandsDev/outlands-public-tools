# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for Python/venvs, fictional work, actual contracts/
settings, stdout captures and qualification receipts:

```text
source/configuration-contract-checker-0.1.0/  selected source only
private/configuration-contract/
  venv312/                                  separate no-pip environment
  fictional_walkthrough.py                  private copy of usage driver
  fictional-demo/                           new authored metadata only
  actual-contract.json                      private declaration
  actual-settings.json                      private values
  captures/                                 caller-owned stdout/diagnostics
  qualification/                            extraction/environments/receipts
```

Select the interpreter and `config_check.py` explicitly. Both `--contract FILE`
and `--settings FILE` are required. No default/environment input, report writer,
installer, target reader, program execution, network/service probe or setting
mutation exists. Strings resembling paths/commands remain data. The caller
controls stdout captures and can overwrite them; choose new private paths.

The contract declares exact field IDs/keys/types/required flags, bounded integer/
string constraints and integer less-or-equal rules. Settings are flat scalar
booleans, signed 64-bit integers or bounded strings. Do not strip vendor schemas,
invent defaults or coerce actual values to force a configuration into this format.
Keys/choices are case-sensitive and string lengths count Unicode code points;
there is no case folding, Unicode normalization or environment/home expansion.

Absent required fields fail; absent optional fields are NOT_SUPPLIED. A rule
with either missing operand is BLOCKED/DEPENDENCY_NOT_SUPPLIED, even if another
present operand is invalid. Only when both are present and independently PASS
can ordering be compared; otherwise invalid dependencies block. Optional absence
alone can coexist with overall NO_DECLARED_VIOLATIONS when no rule needs it.
That result does not mean an absent value was checked or defaulted. Unexpected
settings keys are counted without naming them.

Results keep declared IDs, field/rule kinds, statuses/evidence, counts and fixed
issues; fields precede rules, both in declaration order. Setting keys, values,
bounds, choices, selected paths and native details are omitted. Retained IDs and
relationships still identify designs. Fixed errors do not anonymize captures,
logs or caller tracebacks. Contracts themselves may contain sensitive key names/
choices/bounds. Keep both controls/results private and review a separate export.

Use fully spelled canonical trusted paths and stable ordinary files. Components
are checked after absolute normalization, without original-suffix prevalidation.
Do not assume original leaf/parent dot/space forms are refused in either role.
Actual fictional Windows probes on Python 3.12.7/3.15.2 accepted canonical,
leaf-dot, leaf-space and parent-dot forms in both roles with exit 0; parent-space
returned 2/INPUT_PATH_INVALID. Inputs/runtime were preserved. This is measured
normalization behavior, without blanket suffix-refusal or alias-safety claims.
Inputs require supported ordinary single-link/type/ancestor identities; observed
links/reparse/special/multi-link inputs and sampled changes are refused. These
are sequential sampled reads, not an atomic/coherent two-file snapshot or a
hostile-filesystem boundary. Writers, rebinding, arbitrary mount/drive aliases,
remote/cloud/virtual/live storage, blocked I/O, power loss and ACL privacy remain
outside acceptance. OS reads can involve network storage without a socket/DNS
probe. Access metadata and Python caches are separate.

Each input is at most 64 KiB; field/rule/setting counts and scalar sizes are
bounded. These are not total CPU/RAM/JSON-depth/deadline/storage quotas. Require
complete JSON and actual exit/status; interruption or stdout failure can leave
partial captures. There is no checker-owned output transaction to roll back.
Authored fictional work is retained without automatic cleanup. Requested modes
depend on OS/Python/ACL behavior and do not guarantee confidentiality.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. No pip distribution, network, account or model is
needed; Python retains separate terms. Build/qualification outputs must be new
private paths outside source with existing parents. Publish reviewed source/
sanitized actual validation only, excluding actual contracts/settings/results,
IDs, personal paths, credentials, private source, binaries and raw logs.
See [USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
