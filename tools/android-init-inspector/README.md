# Android Init Service Inspector

Index literal services, actions, service references, imports and `mount_all`
declarations in explicitly selected saved Android init text. Review duplicate
names, selected-file reference ambiguity and critical/reboot-related markers
without running the configuration. Python 3.12 or newer, standard library only,
original [MIT source](LICENSE).

This is a deliberately limited text index. Imports and mount targets are never
followed. Services are not started, and triggers/properties, queues, actual
execution order and Android-version semantics are not evaluated. An unresolved
reference is not proof that a service is missing from a complete device.
`override` never chooses a winning duplicate.

## Download and fictional walkthrough

Download the [0.1.0 source release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-init-inspector-v0.1.0),
including its ZIP, checksums, usage guide, public validation JSON and build
manifest. Verify downloaded hashes before extracting to a new owned directory.
The ZIP contains 29 reviewed source files plus their manifest, 30 members;
Python, actual device configs, generated reports and raw validation logs are excluded.
No pip package, administrator permission, device, firmware or Android installation
is required. Keep the module intact, including `text_support.py`.

The [executable guide](USAGE.md) creates fictional rc text, checks clean and
review findings, independently verifies input/report hashes, compares privacy
modes and exercises controlled refusals. It never executes declarations. Choose
an existing absolute private work directory outside this source folder, and use
a new destination for every generated fixture/report directory.

From this module folder, after setting your existing private directory:

PowerShell 5.1 or newer:

```powershell
python -E -s -B examples/generate.py --output "$privateWork/init-demo"
python -E -s -B init_inspector.py --file "$privateWork/init-demo/clean.rc" --output "$privateWork/init-clean-report"
python -E -s -B init_inspector.py --file "$privateWork/init-demo/review.rc" --output "$privateWork/init-review-report" --include-details
```

POSIX shell, using `python3` if that is your selected Python command:

```sh
python3 -E -s -B examples/generate.py --output "$privateWork/init-demo"
python3 -E -s -B init_inspector.py --file "$privateWork/init-demo/clean.rc" --output "$privateWork/init-clean-report"
python3 -E -s -B init_inspector.py --file "$privateWork/init-demo/review.rc" --output "$privateWork/init-review-report" --include-details
```

The clean example exits 0 with one service and a reference to its unique selected
declaration. The review example intentionally exits 1: duplicate service names,
critical/reboot markers, an unresolved selected reference and an unfollowed
import need review. `override` retains both declarations. Read static local
`report.html` or machine-readable `report.json`.

## Selected text and interpretation

```text
python -E -s -B init_inspector.py --file ABSOLUTE_RC_FILE --output NEW_ABSOLUTE_DIRECTORY
```

Repeat `--file` up to 32 times. Reference resolution spans only those explicitly
selected declarations, using exact case-sensitive names. No input discovery,
import traversal, namespace/device state or complete configuration is inferred.

The supported subset includes literal `service`, `on` and `import` headers,
selected service-option keywords, action `start`/`stop`/`restart`/`exec_start`
references and `mount_all` declarations. Service option operands, executables,
triggers, numeric flags and permissions are not validated for runtime meaning.
Quoted/escaped/continued or `$`-expanded noncomment statements produce coverage
and reset section context; later statements cannot attach to a partially
understood header. Inline comments are not stripped. Full-line comments and
blank lines are ignored. See the unchanged [precise subset](docs/FORMAT.md).

References are `unique_selected_declaration`, `ambiguous_selected_declarations`
or `not_declared_in_selected_files`. These are index observations, not proof of
effective service availability. Critical/reboot findings describe markers only,
not a boot risk diagnosis. Empty/comment-only files can have no findings and
exit 0; that says nothing about configuration completeness or device bootability.

## Reports, privacy and exits

Every completed run creates exactly `report.json`, escaped static `report.html`
and `MANIFEST.json`. The manifest records SHA-256/byte lengths for both report
payloads. Input hashes identify exact selected bytes. Unsigned manifests are
consistency checks, not authenticity, author identity or redistribution permission.
HTML has no scripts or external resources. Stdout uses fixed status/count/error
fields instead of input names, paths, values or upstream exceptions.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding/coverage issue in the selected supported text; empty scope can qualify. |
| 1 | `REVIEW_REQUIRED` | Findings or unsupported/incomplete selected scope needs review. |
| 2 | `INCOMPLETE` | Arguments, input/path/encoding, bounds, changed snapshots or I/O prevented completion. |

Defaults omit literal service names, executable/import/mount paths and trigger
text. `--include-details` adds those selected declared fields and reference
names. Raw service arguments are always omitted; only their count is recorded.
Unsupported command text and option operands are not emitted. Opaque IDs, hashes,
line positions, options/counts and structure remain, so omission is not
anonymization. Keep real configs and identifying reports private and review
details carefully before sharing. See [private workspace guidance](docs/PRIVATE-WORKSPACE.md).

## Inputs, bounds and failure limits

Use explicit stable regular local files with absolute paths and owned output
parents. Links/reparse routes, parent traversal, UNC/device paths, Windows
alternate streams, same-file/hardlink aliases, non-UTF-8 and unsupported controls
are refused. UTF-8 BOM, LF and CRLF are supported. The output parent must already
exist, and the destination must be new. A write error can leave a partial new
report directory; preserve/review it and choose another new name after fixing
the cause. Inputs and earlier reports are not edited or silently replaced.

Limits: 32 inputs, 1 MiB each, 4 MiB total, 20,000 physical split lines including
the final empty line, 8,192 characters per line, 4,000 rows per bounded collection
and 8 MiB per JSON/HTML payload. Lines are not joined. Bounds fail incomplete
rather than silently truncating a result.

Snapshot/path checks address ordinary changes, not an OS sandbox or atomic
snapshot against a hostile concurrent writer. Use trusted stable files/parents.
No recursive scan, network, shell/subprocess, privileged operation, service
execution, mount or device access is implemented in the inspector.

## Qualification and feedback

The [qualification contract](docs/QUALIFICATION.md) requires exact pinned CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows/Ubuntu, preserving all 29 original
methods and adding 30 copied-runtime methods. Eight lanes select 472 methods;
accepted passes and exact native skips appear separately in release validation.
Fresh application environments have no pip and zero installed distributions.
The unchanged [historical validation](docs/VALIDATION.md) remains a distinct earlier record.

From this module folder:

```text
python -E -s -B source_check.py
python -E -s -B -W error -m unittest discover -s tests -v
```

See [provenance](docs/PROVENANCE.md), [contributing](CONTRIBUTING.md) and
[security](SECURITY.md). Minimal fictional reproductions and usability ideas are
welcome through the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Do not submit real firmware/configs, customer data, credentials, device
identifiers, private paths or unredacted reports. Inspected inputs retain their
owners' licenses and rights; inspection grants no permission to redistribute them.
