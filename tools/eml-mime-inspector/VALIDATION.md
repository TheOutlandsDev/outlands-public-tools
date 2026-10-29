# Validation and boundaries

The dedicated notification-tools-checks workflow runs Python 3.12 and 3.13 on
Windows and Ubuntu. It checks source manifests, invented core cases, native
filesystem guards and actual standalone CLI/interop acceptance. Required native
hardlink and symlink/junction fixtures must run; the single opposite-platform
method is skipped per tool. Local filesystems may explicitly skip unsupported
link creation, which does not qualify that platform's native boundary.

Tests cover valid examples, invalid structures, relevant injection/ambiguity,
resource limits, exact input pins, deterministic output and privacy defaults.
Actual CLI checks copy each tool independently, run source_check.py, create fresh
external reports, refuse overwrite, omit supplied argument errors and exercise
public fake-outbox acceptance/response-loss semantics. These are synthetic
functional tests, not a penetration test or guarantee on every OS/filesystem.

No actual sending, provider credentials, DNS/mailbox access, real acceptance or
delivery, HTML/mail-client rendering, malicious attachment execution or original
private application workflow is tested. MIME refusals are intentional subset
limits. Windows inherits parent ACLs; no confidentiality claim. Resource bounds
are parser/application checks, not OS CPU/memory quotas or an adversarial sandbox.
Full-drive and original-family rights/privacy clearance remain incomplete.
