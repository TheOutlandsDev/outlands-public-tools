# Manufacturing demo desktop evidence contract

This is preparation for [the unreleased demo in PR #76](https://github.com/TheOutlandsDev/outlands-public-tools/pull/76).
No clean Windows acceptance is claimed. The fixture workflow tests the validator
on invented records and a tiny invented ZIP; it does not run or qualify Windows,
the application, a browser or a VM.

## Frozen candidate

The validator accepts only this reviewed candidate and its original receipt:

- ZIP: `manufacturing-review-demo-0.1.0-windows-x64.zip`
- SHA-256: `e91917577fad09083a0866d8cd49886337404e85d83fba2e4e2377f45c0864f9`
- Packaging revision: `87d9535d3855fac6fc4cc0d07c12dae762991bc6`
- Receipt SHA-256: `be9cf739922bc3387311bc5532bd4ca055d45a6b3785a8c43a5253dc3e4c48e1`

A rebuilt ZIP has a different identity even when application code is unchanged.
It needs its own explicit review and qualification. Replacing a receipt cannot
change these pins. This validator does not rebuild, extract or execute the ZIP.

## Run the real test later

Use the separately prepared desktop packet on a genuinely fresh Windows 11 x64
PC or VM. The operator establishes the fresh-install provenance. The packet's
command/registry preflight is limited; it does not scan the whole disk or prove
the absence of every Python file. Existing Python commands, callable registry
installations or inventory errors require review before the demo runs.

Keep its complete private evidence folder. The gate reads the original
`preflight-private.json`, `qualification-summary.json`, `packages/acceptance.json`
and the saved run under `native checks/private/fresh manual run`. It requires all
eight named native checks, 36 CLI checks, 17 retained expected review outcomes,
runtime isolation, both exercise summaries, exact arithmetic and the original
receipt/input/report hashes. Recomputed outer hashes cannot hide changed receipt
content or incorrect exercise accounting.

Using the packet's included bootstrap interpreter, prepare the observation form:

```text
python -I -B manufacturing_desktop_gate.py --candidate-dir CANDIDATE_PACKAGE_DIRECTORY --evidence-dir PRIVATE_EVIDENCE_DIRECTORY --prepare-observations
```

Use absolute ordinary local paths and replace `python` with the packet's included
`bootstrap-runtime/python.exe`; do not install a separate Python for this test.
The command creates only a new `operator-observations.json`, with record hashes
already bound and every observation unconfirmed. It refuses an existing form.

After personally using Explorer and the desktop browser, fill the form with
what you actually observed. Confirm fresh-environment provenance, extraction,
launcher use, the report opening, retained review outcomes and saved-report reopen.
Record capacity peaks 3 then 2; five motors reserved against stock four;
inspection coverage 3/4 then 4/4; and cohort four as two first-pass good, one
reworked good and one scrap. Unobserved or disagreeing values must stay unconfirmed.
Then repeat the command without `--prepare-observations`.

## What the result means

`CONSISTENT_REQUIRES_HUMAN_REVIEW` means the pinned bytes, recorded checks and
asserted observations agree. A file can be fabricated: hashes do not authenticate
execution, and operator confirmations remain assertions. The output explicitly
reports that execution authenticity and whole-disk Python absence are unproved,
and `publication_authorized` is always false. A missing record, changed hash,
missing check, unconfirmed observation or unsupported environment is rejected.

`FIXTURE_VALIDATED` is reserved for tests with an injected fictional policy.
The production CLI has no fixture-policy override and rejects the invented ZIP.
No fixture result can stand in for the real run.

The CLI prints only result codes, counts and hashes. It never prints raw records,
paths, exception text or tracebacks. Raw preflight, reports and logs stay private.
Reads are bounded and refuse links, junctions and hardlinked files; inputs must be
stable caller-owned local trees. These checks are not hostile-filesystem isolation.

The existing publisher and blocked hosted cleanup gate remain unchanged. A
reviewer must inspect genuine native evidence and the operator observations,
then explicitly integrate the approved route with publication. This preparation
does not create a release, remove software, alter Defender or start a VM.
