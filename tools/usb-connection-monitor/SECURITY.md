# Security and privacy boundaries

The desktop starts idle. Scanning and monitoring use fixed read-only Windows
PnP queries only after explicit actions. A single app-owned child query is
bounded and cancelled/terminated on request. The app does not elevate, reset
devices, change drivers/settings, capture media, upload files or accept arbitrary
PowerShell commands. The selected ID never enters PowerShell source.

Selection lists/IDs and local screen/shell history remain private. Session
reports intentionally omit identity fields, wall-clock dates and raw output,
but timing/patterns can still identify a session. This is not anonymization or
a universal metadata scrubber. Inspect real reports before sharing them.

Use trusted Python/Tk/Windows components and stable local file parents you
control. File checks are not a hostile-filesystem sandbox, inherited-ACL audit,
encrypted store, or power-loss transaction guarantee. A failed fresh write may
leave partial output. No automatic deletion or cleanup runs.

Never post secrets or real device logs in a public issue. Use the repository's
private vulnerability reporting option if it is enabled; otherwise request a
private reporting channel without including sensitive details. Public issues
should contain only a minimal invented reproduction.
