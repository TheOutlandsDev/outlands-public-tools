# Security and privacy

Use GitHub private vulnerability reporting if the repository offers it. Otherwise
open a minimal public issue asking for a private reporting channel; omit exploit
details, binaries, credentials, private paths and reports. No response time is
guaranteed.

The parser never executes inspected binaries or uses their strings as commands.
Limits and range checks reduce work on malformed metadata; this is not a sandbox
against every hostile filesystem or blocked OS call. Select trusted local storage
and stable input parents. Existing links/reparse points are rejected best effort;
concurrent path replacement can evade ordinary path checks.

Reports can identify private files or embed interpreter/RPATH/RUNPATH strings.
They remain private by default and contain no scanned binary bytes. Hashes do not
establish origin, runtime safety, redistribution rights or authenticity. Candidate
matching is limited metadata evidence, not a security or compatibility verdict.
