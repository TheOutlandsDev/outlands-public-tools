# Browser acceptance and release checks

The application uses Node.js 24 and the pinned runtime npm graph. Browser testing
has a separate development-only package lock under `browser/`; ordinary users do
not need Playwright or a browser installation command.

## Reproduce

From this application folder, after `npm ci`:

```text
npm ci --prefix browser
npm run test:browser -- --install-browser
```

On PowerShell, use `npm.cmd` when the script policy blocks `npm.ps1`. Later runs
can omit `--install-browser`. The runner uses the pinned Playwright 1.64.1 package
and its Chromium build. Linux CI also installs that build's OS prerequisites.
Local Linux users must supply the prerequisites documented by
[Playwright](https://playwright.dev/docs/ci#linux).

The browser test creates an original fictional site outside the application
source, uses a generated password sent to new-only setup through private stdin,
starts the actual loopback server, and uses separate editor/public browser
contexts. It does not reuse a browser profile or an existing website. SMTP stays
disabled. Temporary app/data/backup directories are removed only after checking
their generated fixture root; dependency/browser caches remain for later runs.
Set `SITE_ACCEPTANCE_TEMP` to a writable absolute directory outside the entire
checkout if the default OS temporary directory is restricted.

## The complete workflow

1. Create credentials without printing the password; refuse a second setup and
   preserve the first credential file.
2. Log in; save and reload “Weekend repair guide” as a private draft. A separate
   public browser still sees “Welcome”.
3. Explicitly publish; the public page now shows the new headline.
4. Save “Next workshop guide — draft only” without publishing it. Refuse an
   attempted backup while the editor owns the site.
5. Stop cleanly with exit code zero, create and verify an offline backup, and
   compare the stopped source's hashes before/after. Credentials are excluded.
6. Refuse a deliberately tampered backup. Restore the intact backup into a new
   directory; every restored member matches the manifest. Refuse a second restore
   into that existing directory, preserving its bytes.
7. Restart using the restored data. The public page retains “Weekend repair
   guide”, while the logged-in editor reopens the newer private draft.

This is **one browser acceptance test**, in addition to the **32 integration
tests**. It covers the ordinary workflow and named recovery failures; it is not
power-loss, remote-hosting or production acceptance.

## CI and retained evidence

The collection's `site-builder-release.yml` workflow runs this scoped release
check on Windows and Ubuntu for application/workflow pushes and pull requests,
version tags and manual dispatch. It installs the two pinned npm graphs, verifies
the source inventory, runs all 32 integration tests and the browser acceptance,
checks advisories, and packages the exact committed source. The copy of
`.github/workflows/checks.yml` in the focused download supports a standalone
checkout. Existing collection-wide workflows remain in place.

Each platform's acceptance artifact contains a phase/version summary and actual
screenshots of fictional pages. A failure adds an editor screenshot when
available and a failed phase. Retention is 14 days. Traces, HAR, cookie state,
`.env`, databases, raw logs and backup payloads are not uploaded. Browser fixtures
do not establish behavior in an existing user's environment.

See [current validation](VALIDATION.md), [release instructions](RELEASE.md) and
[walkthrough/capture provenance](WALKTHROUGH.md).
