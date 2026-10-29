# Batch 61 - Independent notification and email preparation tools

Four fresh generic MIT modules extend already-public notification concepts using
invented contracts and fictional examples. Original private application code,
mail templates, customers/users, routing/provider settings, credentials, paths,
operational records and assets are not selected, imported or executed.

| Independent module | Scope | Limits |
| --- | --- | --- |
| [Message Template Renderer](../tools/message-template-renderer/README.md) | Literal text and entirely escaped HTML | No expressions, includes, raw HTML or MIME composition |
| [Message Envelope Checker](../tools/message-envelope-checker/README.md) | Bare ASCII addresses, restricted headers, declared attachment manifest | No attachment reads/hash verification or deliverability proof |
| [EML/MIME Inspector](../tools/eml-mime-inspector/README.md) | Explicit CRLF/7-bit strict MIME subset, decoded hashes/counts | No body rendering, extraction, general mailbox support or malware scan |
| [Delivery Evidence Reconciler](../tools/delivery-evidence-reconciler/README.md) | Explicit attempt/report evidence, backoff/replay/conflict findings | No sending, retries, provider lookup or real-delivery verification |

Each directory is standalone, Python 3.12/3.13 standard library only, with source
pins, fictional fixtures, tests and checked Windows/POSIX file boundaries copied
from pinned public code. JSON reports require private handling. Parser acceptance
does not sanitize real data or establish rights. Existing public outbox semantics
remain unchanged: acceptance is not delivery; uncertain acceptance cannot authorize
replay or be cleared by later success claims. Evidence is caller-supplied.

The dedicated four-job Windows/Ubuntu matrix checks source pins, fictional
core/native tests and actual independent CLI workflows. Required native link
fixtures must run; only the opposite-platform method per tool may skip. No browser,
SMTP provider, real messages, mailbox, original workflow or production delivery
is qualified. Original-family and whole-drive clearance remain incomplete.

All four modules appear in the source catalog. The catalog family is a navigation
classification; combined packages, browser applications and release assets remain
deferred until the remaining drive audit and additional user list are reconciled.
The fixed Toolkit 0.6.0 catalog/downloads are unchanged.
