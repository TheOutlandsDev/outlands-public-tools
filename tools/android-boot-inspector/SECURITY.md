# Security and private reports

Use ordinary copied images and controlled private input/output directories.
Keep selected files stable while inspecting them. The tool rejects recognized
links, device paths and special files, bounds reads and never decodes payloads.
These checks do not make a hostile concurrently changing directory safe.

Reports omit raw strings and paths but preserve numeric layout and metadata
hashes. Such fingerprints can still identify private builds. Output permissions
follow the operating system and its existing ACLs; portable Python modes are not
a Windows access-control guarantee. Review reports before sharing them.

Report a suspected vulnerability privately using the repository's available
security reporting channel. If none is available, open an issue asking for a
private contact without attaching exploit inputs, credentials or sensitive
reports. Use a minimal fictional description. There is no claim that this
inspector authenticates, audits or certifies firmware safety.
