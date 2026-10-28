# Download acceptance — 1.0.2

This check is run **from a freshly extracted focused release ZIP**, with a fresh
dependency install and synthetic private state outside the app. It needs Node 24,
npm and a new absolute scratch directory with an existing parent:

```text
npm ci
node scripts/download-check.js --workspace ABSOLUTE_NEW_PRIVATE_DIRECTORY
```

It creates a new private `.env` in the extracted app, with a random local
password supplied privately over stdin. Do not run it over a configured site.
Outputs, backups, logs, settings and the raw server output stay private.
The stdout receipt contains only fixed check identifiers and a version.

The workflow checks the actual platform launcher readiness command, starts
the launcher's Node entry point, signs in over real loopback HTTP, saves a
private fictional page, checks its public 404, publishes it and saves a newer
draft. It refuses a running backup, stops/restarts, verifies the session expired,
backs up offline, detects a deliberately changed backup member, restores into
a new directory, refuses to overwrite that directory, then reopens both versions.
Normal server shutdown uses its existing owned-process IPC hook.

The first milestone is repeatable CLI/HTTP behavior, not a fresh operating
system certification. Windows and Ubuntu jobs repeat this check with a new npm
install; runtimes and native prerequisites are provided by those runners.
The [download workflow](https://github.com/TheOutlandsDev/outlands-public-tools/actions/workflows/download-handoff.yml)
publishes new immutable focused ZIPs only after the platform checks and exact
Windows/Ubuntu checksum comparison pass. Existing releases are retained.

No new local browser capture was made for this patch: Browser access was
disabled during the release review. Earlier 1.0.1 interface captures and its
browser acceptance retain their original version/date; they are not 1.0.2 proof.
The existing browser CI runs separately from these download checks.
SMTP, internet hosting, mobile editing, power-loss and hostile concurrent file
changes remain outside the qualification. See [full validation](VALIDATION.md).

## Walkthrough sequence

1. Extract, install and check readiness.
2. Save private → public 404.
3. Publish → public page has the new heading.
4. Save newer draft → stop → backup/verify.
5. Corrupt backup → refused; restore intact bytes → verified.
6. Restore into a new path → reopen both versions; old destination preserved.

The portfolio's terminal/API walkthrough presents the fixed outcomes from this
acceptance receipt. It is an edited explanatory sequence, not an interface
screen recording. [Start here](../START-HERE.md) to reproduce the workflow yourself.
