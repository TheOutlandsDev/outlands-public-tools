# Source packaging and validation

The application runs directly from its source directory; no installer, wheel,
third-party package or runtime binary is required or bundled. Supply Python
3.12/3.13 separately. Select a private stable local parent for runtime state.

```text
python -B stack.py source-check
python -B stack.py package --output NEW_PRIVATE_SOURCE_ZIP
```

The manifest selects explicit relative source/test/doc/example paths, sizes and
SHA-256 values. It excludes itself from recursive hashing and is included as an
additional ZIP entry. Source-check verifies every selected byte without executing
selected source. Packaging uses fixed ZIP timestamps, permissions, member ordering
and uncompressed payloads for reproducibility across Windows/Ubuntu. The source
`.gitattributes` enforces LF checkout bytes. The package command returns the ZIP's
SHA-256, size and file count; compare those values with the actual artifact.

No filesystem paths, original file timestamps, user names, runtime state, generated
reports, provider settings, credentials, downloaded binaries or private audit
evidence are ZIP members. The exact selection remains subject to content review;
a source manifest and matching hashes do not by themselves prove confidentiality
or rights. Files copied into the source tree after publication are not automatically
included by the manifest. Changed/missing selected files fail source-check.

Output creation is exclusive and outside the source checkout. A failed write can
leave an unconfirmed new ZIP; preserve it for private review and select a new
filename for a later attempt. No existing output is overwritten or silently removed.

Dedicated Windows/Ubuntu Python 3.12/3.13 CI runs application/component checks,
the fictional restart demo, source-check and ZIP packaging. The uploaded source
artifact and package receipt contain only that reviewed public source. CLI runtime
workspaces, test process traces and private comparison evidence are not release
assets. See [validation limits](VALIDATION.md) and [component origins](COMPONENTS.md).
