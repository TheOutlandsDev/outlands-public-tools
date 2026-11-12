# Release Preflight

Review a small local component update before applying it. Standalone 0.1.0 is a
source-only release for Windows/Ubuntu Python 3.12–3.15, standard library only.
Verify a pinned candidate inventory, compare selected current
files, check a launcher specification, and obtain recovery guidance. The tool
never downloads, installs, starts, stops, copies, deletes, or executes an input.
An optional report is its only file write.

Get the selected source from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/release-preflight-v0.1.0).
Keep `preflight.py` and `preflight_windows.py` adjacent. No Python interpreter,
pip distribution, dependency binary, actual package/configuration/report or raw
log is bundled. No account, model or network service is required; OS access to
remote storage is separate from network probing. [USAGE.md](USAGE.md) supplies
complete fictional outcomes and input/runtime/prior-output preservation checks.

## Try the fictional fixture

From the extracted module directory, with a selected normal Python:

```text
python -B preflight.py verify --candidate examples/candidate --manifest examples/manifest.json --manifest-sha 101d37961fbb644587f589023b7222d53712f4f2eeaade3aa30a1383c4b3b4bf
python -B preflight.py launcher-check --candidate examples/candidate --manifest examples/manifest.json --manifest-sha 101d37961fbb644587f589023b7222d53712f4f2eeaade3aa30a1383c4b3b4bf --spec examples/launcher.json --spec-sha 7ae108d36cda7a3d214e6e29178d36bb22fe5d17d78f91f4cbe9eb9c531c7d51
```

The fixture payload is a Python script. The check does not run it or establish
that an operating system would launch it directly. Only its listed bytes and
configuration structure are checked.

## Manifest and update plan

Prepare and independently review a manifest outside the candidate directory:

```json
{
  "schema_version": 1,
  "inventory": [
    {"path": "bin/component.bin", "size": 12, "sha256": "<64 lowercase hexadecimal characters>"}
  ]
}
```

Each entry has exactly `path`, `size`, and `sha256`. Paths are relative forward
slash names. The candidate must contain exactly the listed files and their
parent directories. Extra files/empty directories, duplicate JSON keys,
traversal, case collisions, reserved Windows names, links, reparse points,
hardlinks, nonregular files, and observed changes are refused.

Obtain the manifest digest from a separately trusted review or release channel.
Computing a digest from an unchecked download does not authenticate it. Hash
agreement proves agreement with the pin, not authorship, licensing, absence of
malware, or safe application behavior.

```text
python -B preflight.py plan --candidate CANDIDATE_DIRECTORY --current CURRENT_DIRECTORY --manifest REVIEWED_MANIFEST_JSON --manifest-sha TRUSTED_SHA256 --report NEW_PRIVATE_PLAN_JSON
```

The plan records `ADD` for a missing current file, `UNCHANGED` for matching
size/hash, otherwise `REPLACE`, in sorted manifest-path order. It reads
only those paths in the current directory; unlisted current files are not
inspected or selected for removal. Candidate/current roots must be separate
and cannot contain one another. A plan is an observation, not a transaction
or reservation; files can change after it is created.

Reports contain relative filenames and current/expected content hashes. Keep
them private. Console summaries omit filenames, absolute roots, and launcher
argument values. `--report` requires a new file outside the repository and
input roots, with an existing parent. It refuses replacement.

Standalone 0.1.0 narrowly corrects the source-boundary constant block: a new
`_SOURCE_DIRECTORY` and revised `REPOSITORY` assignment recognize the literal
structural `tools/release-preflight` layout, protecting the whole collection;
otherwise the enclosing standalone runtime directory is the protected source
root. All runtime function bodies, Windows backend bytes and original examples
remain preserved. This report-scope fix establishes no deployment/concurrency
guarantee. Report creation requests POSIX mode 0600 where meaningful, not ACL
privacy or encryption. Failure can leave a partial or complete-looking
**unconfirmed new report**: require actual exit/status, retain it privately and
choose a new name for retry. No automatic cleanup, replacement or rollback occurs.

## Launcher specification

A separately pinned specification outside the candidate has exactly:

```json
{
  "schema_version": 1,
  "executable": "bin/component.bin",
  "working_directory": ".",
  "arguments": ["--demo"]
}
```

The executable must be listed and hash-verified. The working directory must be
`.` or an existing relative candidate directory. Arguments are bounded strings
without control characters and are never echoed into the result. Environment
variables, shell command strings, executable search, services, scheduling, and
remote control are outside this format. The check does not validate executable
format, permissions, argument semantics, dependencies, or runtime readiness.

## Recovery

Independently establish a maintenance window and a consistent stopped state.
Make and verify a private backup, retaining its digest separately.
[Verified Transfers](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/tools/verified-transfers/README.md) provides an opaque local
backup/restore helper; its stop flag is only an operator assertion. Recheck the
plan immediately before using another tool to apply changes. Verify the result
before starting the application. If recovery is needed, restore to a new
directory and review before switching. This plan has hashes, not prior file
contents, and cannot undo an update.

## Bounds and validation

Metadata is limited to 1 MiB per input. A manifest permits 4,096 files, at most
256 MiB each and 1 GiB total. Candidate enumeration permits 8,192 entries.
Paths permit 240 characters and 32 parts. Selected current files have the same
byte limits. Verification may reread files; these are per-pass payload limits.
Arguments permit 64 strings, 2,048 characters each and 8,192 characters total.

Exit `0` with stdout `VERIFIED` means the requested checks and optional report
completion passed; exit `2` means fixed `ERROR` refusal/failure. Handled Windows
interruption is `PREFLIGHT_INTERRUPTED`, exit `130`; POSIX/library interruption
retains propagation. There is no `--version` switch; [VERSION](VERSION) is package
metadata. Controls accept UTF-8 BOM but refuse duplicate keys/nonstandard JSON
constants. Pins cover raw bytes. Zero-byte payloads are permitted; verification
may reread inputs, and bounds are not total CPU/RAM/depth/deadline quotas.
Every result states `execution_performed: false`. Use stable local inputs:
this is not a hostile-filesystem sandbox, application-consistency proof, full
game installer, or race-free deployment. Windows/POSIX input and new-report
handling is hardened; see [I/O checks and limits](IO-SAFETY.md) and the
[current review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-33-RELEASE-PREFLIGHT-IO.md). Windows requires
the adjacent `preflight_windows.py`. Native path rules
are stricter; reports remain private and new-file-only. Network/cloud storage,
ACL privacy, power loss and live integration remain unverified. The
[original batch review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-8-REVIEW.md) records initial provenance.

Fresh standalone qualification selects eight Windows/Ubuntu lanes on Python
3.12, 3.13, 3.14 and 3.15.2, with no-pip/zero-distribution environments. It retains
75 original methods (28 shared regression and 47 I/O) plus 26 copied two-file CLI
methods: **101 per lane, 808 selected executions**. Selection is not a passing
result. Actual versions/counts/skips/outcomes belong to release `VALIDATION.json`.
Applicable native fixtures must execute under strict hosted contracts without
policy bypasses. See [QUALIFICATION.md](docs/QUALIFICATION.md).

`IO-SAFETY.md` retains historical wording, layout and evidence, including original
28/new 47-method results, copied-process checks and 100 fictional-tree comparisons.
Those results are separate from fresh standalone archive qualification; its
collection-layout statement predates the narrow scope assignment above. Use one
operator, canonical paths and quiescent trusted local trees. Sampled identities/
held handles do not freeze content or establish atomic snapshots, writer denial,
an I/O deadline, all-stream inspection or an application-consistent backup.
Drive/mount aliases, remote/cloud/live providers and blocked I/O remain outside
acceptance. Reads may affect access metadata; captures/tracebacks stay private.

## Provenance and privacy

Fresh original implementation informed by read-only review of the owner's
server update, checksum, backup/recovery, and launcher preflight methods.
Original vendor downloaders, installation/process controls, monitoring startup,
deployment paths, configurations, credentials, telemetry, schedules, game/plugin
code and vendor assets are excluded. No original script was executed. Operator
inputs/reports can contain private material; this tool does not sanitize them.
Original source and fictional examples use the [MIT license](LICENSE),
which grants no rights in operator inputs or third-party software.
The owner reports personal work created with AI assistance, without exclusive-
authorship claims. User-owned Python/venvs need no inherent administrator access;
respect OS/device policy without bypasses. See [PROVENANCE.md](docs/PROVENANCE.md),
[third-party notices](THIRD-PARTY-NOTICES.md) and
[private workspace guidance](docs/PRIVATE-WORKSPACE.md).
