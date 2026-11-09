# OUTLANDS daily work guide

This page points to reusable source and methods already on GitHub. Start with the smallest tool that fits the task. Each linked repository has its own requirements and validation limits.

## Find and install a tool

1. [Browse the tool catalog](../catalog/generated/INDEX.md) by task and read the linked tool README.
2. For a Python component, use the [selective install guide](../integrations/public-tools-bundle-72/START-HERE.md). Choose one tool or a group before taking the whole bundle.
3. Run the tool's fictional example first. Keep real input, generated reports, and access details in your own private workspace.

## Plan a change

| Task | Reusable method or source |
| --- | --- |
| Define the request, owner, inputs, and acceptance criteria | [Project intake](../methodology/project-intake.md) |
| Inspect source before changing it | [Source inventory](../tools/source-inventory/README.md) |
| Check working trees and local branches | [Git worktree reporter](../tools/git-worktree-reporter/README.md) |
| Record what was checked and what is still unknown | [Validation record](../methodology/validation-record.md) |

## Validate and release

| Task | Reusable method or source |
| --- | --- |
| Check documentation structure and links | [Documentation check](../tools/documentation-check/README.md) |
| Compare dependency locks for a focused update | [Dependency lock diff](../tools/dependency-lock-diff/README.md) |
| Review an exact public candidate before upload | [Pre-upload review aid](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/tree/main/tools/preupload-check) and [public release audit](../tools/public-release-audit/README.md) |
| Record hashes of reviewed artifacts | [Hash journal](../tools/hash-journal/README.md) |
| Decide whether a release is ready | [Release review](../methodology/release-review.md) |

An automated scan is one input to review. Check rights, notices, credentials, private data, and the exact files separately before publishing. A passing local check does not establish live behavior.

## Preserve and rebuild

| Task | Reusable method or source |
| --- | --- |
| Check the shape of a backup chain | [Backup chain checker](../tools/backup-chain-checker/README.md) |
| Write a handoff and a rollback path | [Handoff and rollback](../methodology/handoff-and-rollback.md) |
| Rebuild the WoW server from reviewed source | [Outlands WoW](https://github.com/TheOutlandsDev/outlands-wow) |
| Manage the OTT WWI server | [OTT WWI server manager](https://github.com/TheOutlandsDev/outlands-ott-wwi-server-manager) |

The WoW and WWI repositories are separate projects. Their public source and rebuild steps do not include live server state, player data, or host access. Follow each repository's current README and verification status before deploying.

## Find the owning repository

Use the [public project map](PROJECT-MAP.md) for applications, game projects, and infrastructure guides. Keep project-specific changes in the owning repository; use this collection for reusable tools and methods.
