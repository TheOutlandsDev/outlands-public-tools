# Security and privacy

Resource Monitor reads aggregate CPU, memory and network counters. It does not
inspect packet bodies, addresses, processes, command lines, browser history or
credentials. It contains no outbound HTTP client, reputation lookup, remote
provider, account login or telemetry uploader. The separately installed psutil
package and the operating system have their own behavior and terms.

The HTTP server listens only on IPv4 loopback. Exact Host/Origin validation,
capability-token API requests, static-route allowlisting, a self-only CSP and
bounded requests reduce accidental exposure. No CORS permission is granted.
Tokens are generated per server process and do not appear in API bodies or
request logs. The local startup URL does contain the token in its fragment.
The browser removes that fragment and retains the token only in tab memory.

This is not authentication against other software running as the same user or
isolation from a compromised computer. Keep the server, source assets, terminal,
browser and filesystem trusted. Do not proxy or expose the listener to a network.

Real samples/timestamps can reveal activity and hardware characteristics. Exports
are clear text and are not anonymous or encrypted. Browser downloads, scrollback,
OS logs and manually redirected CLI output can persist after the server stops.
The program does not erase those records. Store exports outside public source.

Explicit CLI export creates a fresh file, refuses linked parents/targets and
does not overwrite. It is not a hostile-filesystem sandbox or crash-atomic
backup; concurrent parent replacement is unsupported and a failed write may
leave a partial new file. Windows permissions are inherited; POSIX creation
requests owner-only permissions.

For reports, share a minimal fictional reproduction and redacted symptoms.
Avoid public capability URLs, real histories, private paths and screenshots that
identify a user or computer. Do not post sensitive vulnerability details in a
public issue before agreeing an appropriate private reporting channel with the
maintainer.
