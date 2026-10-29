# Actions trigger and concurrency policy

Ordinary checks run for matching pull requests and matching pushes to `main`.
This avoids running the same ordinary matrix on both a feature-branch push and its
pull request. Manual dispatch remains available where previously supported.

Workflows that publish artifacts retain feature-branch qualification. Only Toolkit
and Local Site Builder source release workflows accept their explicit release-tag
patterns. Unrelated tag pushes cannot fan out into every component's checks.

Superseded branch/PR runs share a workflow, source-repository and branch group and
can cancel. Main and tag runs use their unique run ID, with cancellation disabled:
they cannot cancel an active release or replace another pending main/tag run.
Permissions, test commands, native fixtures and acceptance checks are preserved.
A read-only changed-path gate additionally keeps workflow-only edits from invoking
main-only artifact publishers. Source changes still require all existing qualification
jobs before publication; manual main dispatch remains available. A missing push
base fails closed. Deletions and renamed-out paths are included in the diff.
A one-time validation of the changed workflows can still run broadly.

`check_workflows.py` parses every workflow with duplicate-key rejection and checks
this policy. Its CI-only PyYAML dependency is hash pinned. It does not install or
run applications. Tests reject broad tags, missing branch/PR filters, unsafe
cancellation, shared protected-ref groups and malformed YAML. The checker does not
execute GitHub expressions or establish the runtime behavior of every action.
