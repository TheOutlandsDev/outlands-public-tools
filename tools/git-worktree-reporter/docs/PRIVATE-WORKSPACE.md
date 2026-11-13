# Private inspection workspaces

Use an existing trusted private parent outside the source checkout, selected worktrees, their Git metadata and public/synchronized directories. Every report must have a new path with an existing parent. Existing inputs, reports and incomplete outputs are never replaced by the inspector.

The fictional guide creates and commits only newly owned disposable repositories. Its setup commands are deliberate fixture operations; the inspector itself does not create commits or modify a selected repository. Do not reuse those setup commands against an existing project. Follow your normal approvals before applying any method to real workplace code or tools.

Actual status reports can disclose relative filenames, renamed paths, branch/ref names, object IDs, source-status hashes and tool versions. They contain no file excerpts, but omission of paths/content is not anonymization. Keep real repositories, `.git` data, reports, manifests, paths and raw diagnostics private. Review any report separately before sharing. A successful local inspection is not secret clearance, a backup or proof of publication rights.

The report uses isolated global/system configuration. Global ignore/attribute/EOL/filter policy can therefore differ from interactive Git; global LFS driver requirements and LFS object preservation are not established. Upstream counts are based on stored local refs and are not refreshed from a server.

A handled I/O failure can retain an incomplete new output. Treat it as unconfirmed, retain it privately and choose a different new destination for a retry. The tool does not remove partial outputs, prune worktrees, recover source or roll back operations.

Use one operator with trusted Git, stable local files and supported configuration. Metadata comparisons and owned-child bounds are sampled observations, not an atomic snapshot, hostile-filesystem/process sandbox, hard native startup/I/O deadline or ACL confidentiality guarantee. Mapped/network/cloud storage and actively changing or malicious repositories are outside qualification.
