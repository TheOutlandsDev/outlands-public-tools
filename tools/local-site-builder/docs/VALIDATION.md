# Validation and limits

## Recorded local evidence

The app was reviewed on Windows with Node.js 24.15.0 and npm 11.12.1. The pinned
dependency installation completed, including the real native SQLite binding.
`npm audit` returned zero known advisories on 2026-10-25.

The automated suite contains **32 generated-fixture tests**, all passed locally
with no skips. It starts actual loopback HTTP servers and uses SQLite and image
uploads; it is not only a syntax check. Coverage includes:

- Fictional default pages, authenticated editor/API access, strict session cookie
  creation/regeneration/logout and login rate limits.
- Forged Host, foreign Origin, missing CSRF and opaque-webview token behavior.
- Templates, reserved/duplicate slugs, private drafts, escaped published text,
  separate published title/description through navigation refresh, and page delete.
- Page depth/list/block/text limits, unsupported blocks/keys, duplicate block IDs
  and request size refusal.
- Image signatures, exact uploaded bytes, randomized names, SVG/fake MIME refusal,
  multipart and 5 MiB upload limits.
- Default contact delivery staying local, escaped inbox content and disabled SMTP.
- Data-lock exclusion while running, stopped backup, exact checksums, manifest
  tampering/unlisted paths, fresh-directory restore, and reopened restored pages,
  private draft, inbox and original image bytes.
- New-only password setup and hash verification, exclusive data locks, and static
  export excluding private state and replacing backend contact forms.

In the actual browser, a generated demo account logged in, loaded the editor,
changed the hero headline, saved the draft, and published it. The separate local
public page displayed the new headline. An opaque Origin from the embedded
browser initially revealed a compatibility problem; session-bound CSRF tokens
now support that case while token-free changes remain rejected. No family site
was launched or modified. A private preparation screenshot is not a user dataset.

## CI

The repository workflow performs a clean lock-based install, source check,
synthetic tests and advisory check on Windows and Ubuntu with Node 24. Consult
[Actions](https://github.com/TheOutlandsDev/outlands-public-tools/actions)
for actual run results. Workflow configuration alone is not evidence of a passing
platform run. The suite uses generated data exclusively and makes no SMTP call.

## Explicit limits

- This is a single-user local editor. It has memory-only sessions, no public
  hosting support, tenant isolation, account recovery, roles or revision history.
- It has not received an independent penetration test or accessibility audit.
  The visual editor was checked at a desktop width; mobile editing is unqualified.
- CSP permits inline code/styles because the original renderer emits them. This
  is defense in depth, not a claim that arbitrary hostile input is safe.
- Image signatures are shallow format checks, not full decoding or metadata
  removal. External image references can disclose visitors' request metadata.
- Draft/menu/page publication involves filesystem and SQLite operations without
  a cross-resource atomic transaction. Disk failure can leave incomplete generated
  HTML or a failed publish that needs retry. Back up before destructive edits.
- Backup/export require stopped, trusted local data and reject a nonempty WAL.
  Checksums are not signatures. Storage/path checks do not defeat adversarial
  races, every reparse tag, network filesystem semantics or power loss.
- Abrupt termination may leave the lock marker. Confirm no owner is active before
  manual recovery; never suppress ownership checks to force a pass.
- Restore runs only into a fresh directory and does not migrate the private
  family's schema. Backup intentionally excludes credentials and dependency/runtime
  installation; it is not a complete machine backup.
- Remote SMTP delivery, internet hosting, macOS, large production sites, long-term
  operation and unattended service management remain unqualified.
