# Security and privacy

Launch receipts and errors can reveal executable paths, working directories,
PIDs and arguments. Terminal scrollback, shell history, redirected output and the
selected application's own logs may retain these values. Redact reports before
sharing them; the tool is not an anonymity or secure-erasure mechanism.

Use a trusted executable and stable local files and parents. Path checks do not
turn the filesystem into a hostile-writer sandbox or establish an application's
trustworthiness. The selected application runs with the calling user's normal
rights and can interpret its arguments, access files and create other processes.

The launcher uses an explicit executable and no shell. It does not elevate,
install a service, change registry settings, connect to the network or change
existing processes' affinity. Setup-failure cleanup targets only its newly
created child handle. Optional wait timeout or interruption leaves a resumed
application running.

Duplicate checks have visibility and timing limits. Report unqueryable/truncated
enumeration honestly; do not interpret a lack of visible matches as proof that
no other copy exists.

For a security report, describe the affected source version and a minimal
fictional reproduction. Do not post sensitive operational records publicly. Use
the account's available private reporting route if suitable; no confidential
issue channel or response deadline is promised by this document.
