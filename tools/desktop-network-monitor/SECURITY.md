# Security and privacy

Startup is idle. Live capture and external reputation requests are explicit
opt-ins; they do not run in the demo/replay or at import. The selected capture
interface and online address are user decisions. Only capture on interfaces you
are authorized to inspect. Capture and OTX do not block, alter or probe traffic.

The application has no automatic CSV/log/payload export. Aggregate reports use
an allowlist and omit addresses, interface/host names, dates, paths and secrets.
These omissions do not make counts/structure anonymous. The native packet stack
handles bytes in memory, and native diagnostics, shell history or screenshots
may expose local details. Keep actual records outside the source repository.

The fixed OTX HTTPS endpoint does not follow redirects. Requests disables
environment-proxy and .netrc discovery; it uses the explicitly configured OTX
key and normal TLS verification. Capture never submits addresses automatically.
Parent worker budgets terminate only app-owned children. A cancelled/terminated
request cannot retract an address already sent after your explicit approval.

This is not an intrusion-prevention system, causal diagnosis, encrypted store,
hostile filesystem sandbox, universal metadata scrubber or a guarantee about
the remote service's accuracy. No elevation/driver install or system-policy
change is performed. Failed fresh writes can leave partial output; review them.

For a vulnerability, use GitHub private reporting if enabled or request a private
channel without disclosing sensitive material. Public issues need invented data.
