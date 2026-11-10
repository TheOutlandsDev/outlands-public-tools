---
name: check-bedrock-readiness
description: Check Kiro model selection or a direct AWS Bedrock pairing plan without signing in, resolving credentials, or calling a model.
---

Establish whether the user needs Kiro's managed GPT access, direct Bedrock SDK
access for an application, or both. These are separate credentials and access
qualifications. Use the managed Kiro picker for Kiro model IDs. A Bedrock API
model ID does not establish that Kiro exposes it.

For an installed kit, inspect .kiro/devkit/pairing-plan.example.json and use
python -B .kiro/devkit/check_bedrock.py --plan followed by the local plan path.
The check accepts declarations only, never keys or tokens. Leave direct
Bedrock disabled unless it is actually required. Do not request credential
values, read auth caches, run an AWS credential chain, or start sign-in as
part of an offline check. If SDK dependencies are already present, --probe-sdk
uses dummy auth and in-memory HTTP with sockets blocked.

Report plan completeness separately from live access. Installation permission,
organization sign-in, model availability, IAM access, and network reachability
remain unverified until separately checked in the managed environment. When
the user authorizes live testing later, use the organization's documented
account and regional route and preserve the actual client evidence locally.
