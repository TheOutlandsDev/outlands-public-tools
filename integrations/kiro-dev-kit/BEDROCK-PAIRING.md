# Kiro and Bedrock readiness

Kiro model access is configured through your organization's Kiro sign-in and
model governance. Direct Bedrock API access is a separate application setup.
Kiro availability does not establish that an AWS profile or API key is
available for your own SDK applications. Start with the Kiro route; request
direct SDK access only if your task actually requires it.

## Inspect a laptop without installation or admin

The standalone [Inspect-KiroLaptop.ps1](scripts/Inspect-KiroLaptop.ps1) uses
Windows PowerShell metadata commands. It does not need Python, invoke a found
application, start an installer, request elevation, inspect credentials,
change policy, write a report, or contact an endpoint. Run it in ordinary
Windows PowerShell only when local policy permits scripts:

```powershell
./scripts/Inspect-KiroLaptop.ps1
```

If script execution or a query is blocked, retain that result. Do not change
execution policy or application-control settings. Check Company Portal or
Software Center and the company's deployment instructions. The report uses
UNKNOWN/NOT_DETERMINED for unreadable settings and installation permission;
there is no read-only guarantee that an eventual installation will succeed.
PATH discovery can miss installed software. A Python WindowsApps alias does
not prove a usable Python runtime. Execution policy concerns PowerShell
scripts. DisableMSI concerns Windows Installer packages and does not establish
whether the Kiro IDE EXE or a managed deployment is permitted. AppLocker/WDAC,
network controls, and administrator approval are not evaluated by this script.
Normal company auditing can still record these metadata reads.

The output omits machine name, username, domain, discovered executable paths,
profile names, credentials, and raw exception messages. Review it locally
before sharing. These checks inspect the computer where you run them; a
personal PC report does not qualify a separate work laptop.

## Prepare a local pairing plan

Use [pairing-plan.example.json](pairing-plan.example.json) as a local worksheet.
It contains no credentials and initially leaves direct Bedrock disabled.
Record exact approved Kiro model IDs from the managed picker and select one
from that list. Keep the filled file outside the public checkout.

```powershell
python -B scripts/check_bedrock.py --plan pairing-plan.example.json
```

Installed projects receive the same checker and empty template under
`.kiro/devkit/`. The checker never reads an AWS configuration file, credential
cache, environment credential, or network service. It validates declarations,
checks endpoint/model identifier shape, derives the AWS endpoint, and flags
the documented GPT-6 Mantle region mismatches. Every report retains
`ready_for_live_work: false`; a complete plan is not account-access proof.
Unknown fields are rejected so this worksheet cannot become a credentials
file. Error output does not echo supplied values or private paths.

For direct SDK work, declare the approved region, endpoint, model ID, and
authentication method: AWS profile, environment credentials, or Bedrock API
key. The profile name is optional private metadata and is not printed in the
report. Do not paste keys, tokens, account IDs, or SSO URLs into this worksheet.
Credential expiration, permissions, model subscription/access, billing,
regional availability, proxy/TLS access, and actual inference stay unverified.

## Keep endpoint and model identifiers together

| Route | OpenAI-compatible base URL | Model identifier shape |
| --- | --- | --- |
| Bedrock Runtime | `https://bedrock-runtime.REGION.amazonaws.com/openai/v1` | Supported inference profile such as `us.openai.gpt-6-sol` |
| Bedrock Mantle | `https://bedrock-mantle.REGION.api.aws/openai/v1` | Supported base ID such as `openai.gpt-6-sol` |
| Kiro chat | Managed by Kiro | Exact ID available through its picker |

The checker models the documented GPT-6 US/Global profile shapes; it is not
an exhaustive AWS model catalog. Mantle GPT-6 Sol/Luna use us-east-1 and Astra
uses us-west-2 in the documentation snapshot. Runtime cross-region profile
availability and IAM permissions must be confirmed for the source region.
Do not interpret a structurally valid unknown model as a supported deployment.

## Exercise the Python SDK without AWS

The optional SDK check is pinned to OpenAI Python 3.48.0. Install its
dependencies only in an approved local development environment:

```powershell
python -m pip install -r requirements-bedrock-check.txt
python -B scripts/check_bedrock.py --probe-sdk
```

It executes four request/response cycles in memory: Runtime and Mantle, each
with dummy bearer and explicit dummy SigV4 credentials. It checks the host,
Responses path, model ID, auth scheme, signing service, and parsed response.
Sockets are blocked, ambient environment is cleared during the probe, no AWS
credential chain is requested, and no real key is accepted. A pass establishes
SDK construction/serialization only, with zero service requests or charges.
The HTTP transport is the SDK's pinned httpx2 dependency; this is an authoring
check, not a mandatory dependency of the kit installer.

When direct API access is later authorized, the standard provider can use an
approved AWS profile with explicit `api_key=None` to select SigV4 instead of an
ambient bearer token. Your application supplies the supported region and
endpoint together. Reuse the organization's authentication method rather than
creating a new long-lived key simply to run a readiness check.

For Node and Java, the companion [SDK examples](../windows-ai-readiness/README.md)
retain their import/compile/offline boundaries. The four in-memory signing
checks above qualify the pinned Python SDK, not those other SDK transports.

## Managed acceptance

First complete the Kiro sign-in, selected-GPT, read/edit/test, independent
review, and handoff exercises in [ACCEPTANCE.md](ACCEPTANCE.md). If direct SDK
access is needed, separately have the owner confirm the AWS source region,
model/profile, identity permissions, supported endpoints, and approved auth
method. An authorized minimal live request is a later step; this kit does not
perform one. Keep Kiro and SDK evidence as separate records.

Sources checked 2026-11-09: [Kiro organization authentication](https://kiro.dev/docs/getting-started/authentication/),
[Kiro governance](https://kiro.dev/docs/enterprise/governance/),
[OpenAI on Bedrock](https://developers.openai.com/api/docs/guides/amazon-bedrock),
[OpenAI Python SDK](https://developers.openai.com/api/reference/python),
[AWS GPT-6 Sol](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-sol.html),
and [Microsoft DisableMSI](https://learn.microsoft.com/en-us/windows/win32/msi/disablemsi).
