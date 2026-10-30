# Five-minute fictional software-quality review

One invented service request connects five independent offline checkers. The
operator wants priority **5** recorded; Boolean `true` is not an integer priority.
This is an original public demonstration, using no employer schema or records.

## Requirements and quick start

Use the repository source at the revision containing this guide, with Python
3.12 or 3.13 supplied separately. Standard library only, Windows or Linux.
Toolkit 0.9.0 does **not** contain these newer tools or this runner. No installer,
browser, network service, API key or real service request is needed.

From the repository root:

```text
python -B workshops/software_quality_review.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

Replace the placeholder with a fresh absolute folder outside the source checkout,
under an existing trusted parent. The runner refuses existing destinations,
linked parents and folders inside the checkout. It never overwrites a prior run.
On Windows, quote a path containing spaces. On Linux, choose a directory you own.
The expected console summary is `PASS`, **10 command checks**, **5 expected review
outcomes**. This summary means the exercise matched its expectations; five
underlying reports intentionally retain `REVIEW_REQUIRED` and exit code 1.

## Follow the failure and correction

| Stage | Retained failure | Correction and expected result |
| --- | --- | --- |
| Form submission | `priority: true` has `type_invalid` | New submission revision uses integer 5; PASS |
| API request | The same typed value fails the declared JSON body field | Same invented values, explicitly mapped to the request body; PASS |
| API response | Supplied `accepted: "yes"` is a string, not Boolean | Revised supplied response uses Boolean true; PASS |
| Interaction history | A `valid` guard refuses the invalid submission; last confirmed state remains `draft` | Bind the corrected submission; declared terminal state becomes `recorded`; PASS |
| Version comparison | Revision 2 narrows maximum priority to 4; identical priority-5 observation fails | Revision 3 restores maximum 5; the same selected observation agrees with baseline; PASS |

All form, operation, submission and flow references use their exact normalized
definition hashes. A changed definition receives a new revision. The comparison
keeps the same selected values and events, changing only verified version bindings.
It does not swap in easier observations to make a regression disappear.

## Inspect what actually ran

`inputs/` retains ten generated fictional input files. `reports/` retains the ten
actual tool reports, including failures. `result.json` records each expected and
observed status, exit code, input/report SHA-256 and the tool Python source hashes.
The runner independently checks field types, last confirmed states, terminal
outcomes and range regression, then checks its inputs and tool source stayed
unchanged. An unexpected failure stops completion and leaves its private partial
files in place. Choose another fresh folder for a new attempt.

To independently hash any retained file, use `Get-FileHash -Algorithm SHA256`
in PowerShell or `sha256sum` on Linux, and compare its hexadecimal digest with
the matching entry in `result.json`. Hashes bind bytes; they do not authenticate
who executed a run. Do not publish private runs containing real records.

## Design decisions, contribution and limits

The exercise deliberately connects existing tools through explicit fictional
inputs rather than claiming automatic form-to-API integration. Type rules stay
strict; no Boolean-to-integer coercion, default insertion or silent history repair.
The response is a supplied observation, not a captured server reply. The history
describes a state graph; it does not prove a browser interaction or human approval.
Comparison PASS covers these selected observations, not whole-application
compatibility, accessibility, authentication or production behavior.

This workshop adds orchestration, independent outcome checks and a reproducible
handoff around the existing tools. It was implemented and reviewed with AI
assistance for this public portfolio task; it makes no new claim about personal
contributions to the underlying projects. Automated CI execution is linked from
the change's checks. Clean Windows application acceptance remains a separate task.
