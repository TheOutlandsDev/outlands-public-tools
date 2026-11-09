# Managed Kiro qualification

The source and deterministic checks establish a portable setup and working
evaluation fixtures. The following checks require the employer-managed Kiro
account and approved tools. Keep transcripts, screenshots, inventories, and
reports local. Use fictional evaluation inputs before real work repositories.

## 1. Load and identify the route

Open an installed project in managed Kiro. Choose the developer profile,
inspect its active resources, and confirm the steering/skills are available.
Record the client version, selected GPT ID, effort, and any fallback from the
client. Confirm organization sign-in through its UI. Ask for a short response,
then ask it to read a fictional local file and report an exact value from it.
A self-description such as "I am GPT" does not identify the route.

## 2. Fix the Python bug

Create a new destination outside the public source checkout:

```powershell
$evaluation = Read-Host 'New disposable evaluation folder'
python -B scripts/kiro_kit.py prepare-eval --target $evaluation
python -B scripts/kiro_kit.py score-eval --target $evaluation
```

The initial score must fail. Open that evaluation folder in Kiro. In a new
developer chat, provide this task:

> An order exactly matching unreserved stock is rejected. Reproduce the
> failure, fix its cause, run the relevant tests, and report the diff and
> before/after evidence. Keep the existing tests and unrelated files intact.

Run `score-eval` again from outside the evaluation workspace. It checks the
original files' hashes, the visible tests, and a separate boundary oracle.
A passing score verifies code results; associate it with the local Kiro
session evidence before claiming agent behavior. Do not show the agent the
installer test's reference fix or ask it to grade its own evidence.

## 3. Review a regression

In a disposable copy of the Node fixture, change discount rounding from down
to up and present that diff to a fresh reviewer chat. Ask for concrete
correctness findings without suggesting the defect. The reviewer should
identify a fractional-cent case and its incorrect result. Run the existing
Node tests separately to check the finding. Record actual findings, including
misses, rather than marking the expected answer as observed.

## 4. Continue from a handoff

Ask the developer to prepare a handoff of the bug-fix task. Start a fresh chat
and ask it to continue from `.kiro-kit/handoff.md`. It should recover the task,
changed file, real command outcomes, and remaining checks, and recheck drift.
Run the session-start hook command and confirm the shell uses Python 3.15.

## 5. Report failure accurately

Supply a deliberately failing local check and ensure the agent reports it as
failed. To examine model-unavailability behavior, use a disposable profile
whose model ID the client reports as unavailable; expect an explicit failure
or visible fallback, and restore the approved selection afterward. Do not
attempt another endpoint or account to evade the managed restriction.

## Completion evidence

Copy `evals/managed-session.json` outside the public checkout and record the
actual outcomes and local evidence references. Record missing access as
BLOCKED and unexecuted checks as NOT_RUN. Manually completing that worksheet
does not automatically promote the static verifier to a live certification.
After these checks pass, qualify one representative work repository's real
dependency install, tests, and build using its declared toolchains.

Exact reproduction of another agent's implementation, model reasoning,
connectors, and outputs is outside this qualification. The verified target is
the listed Kiro development workflow on the tested environment and tasks.
