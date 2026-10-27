# Validation and limits

All fixtures are invented messages and fake adapter outcomes. No original service
code, provider account, recipient list, template, operational record or message
is read, copied, executed or sent.

The 45 methods cover token/text/UTF-8 limits, controls and invalid Unicode,
immutable values, defensive copies, duplicate/conflict behavior, retained key
capacity, snapshot minimization, clock/limit bounds, explicit retry scheduling
and exhaustion, permanent rejection, adapter acceptance, invalid acknowledgments,
uncertain outcomes, acceptance followed by a lost response, callback reentrancy,
control exceptions, matching caller delivery reports, fake cache/script limits,
fixed CLI errors, actual CLI preservation and file/network/process canaries.

From the repository root:

```text
python -B -W error -m unittest discover -s tools/notification-outbox/tests -v
python -B tools/notification-outbox/demo.py --demo
```

The dedicated workflow runs all 45 methods without skips on Windows/Ubuntu
Python 3.12/3.13, the actual fictional demo and collection Markdown/JSON checks.
Before publication, a standalone copy is exercised against an independently
authored outcome/state oracle; exact selected file bytes are privately audited.
Generated private logs, state histories and reports are not publication files.

These checks establish the documented bounded synchronous state transitions.
They do not validate a real adapter's failure assertions, real delivery, provider
idempotency, threading, atomic process interruption/crash recovery, persistence,
business authorization, privacy clearance or production usefulness. A fake's
acceptance cache provides evidence only about that fake. No real SMTP/provider,
durable store or private source adapter is included or tested.
