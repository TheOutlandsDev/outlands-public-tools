# Five-minute fictional setup review

Use the complete Toolkit 0.6 source ZIP with Python 3.12/3.13 supplied separately.
Choose a new absolute private directory with an existing trusted parent outside
the extracted package. Five minutes is approximate, not a measured performance claim.

From the extracted package root:

```text
python -B workshops/lifecycle_exercises.py --exercise setup --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

1. Save the invented setup profile: two prerequisite declarations, two integer
   settings and their rule, two required filenames, two loopback bindings and
   three dependency-ordered manual steps.
2. Evaluate the supplied observations with `sample_runtime` declared `MISSING`.
   One blocking check holds all three steps. Nothing is discovered or executed.
3. Evaluate a new supplied observation revision declaring that prerequisite
   `PRESENT`. Expect nine checks and zero blocked steps, with the step order
   `prepare`, `review`, `handoff`. This satisfies declarations only: runtime
   verification and all three manual verifications remain unperformed.
4. Observe that missing quality review refuses a plan. Review explicitly, create
   the plan and export a six-file private handoff. Independent hashes verify all
   five manifest entries plus the manifest file. No execution/publication permission
   is granted by the handoff.
5. Reopen the instance and inspect its profile, two evaluations, plan and eight
   journal events. The two original input fixtures and fictional target sentinel
   remain unchanged. The automated exercise records 19 original CLI calls.

To inspect the saved workflow in the browser, substitute the same actual directory
used above, append `/setup`, and run from this complete package root:

```text
python -B systems/environment-setup-workbench/workbench.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY/setup serve
```

Open the printed local address. Inspect the two evaluations and saved manual plan.
Stop the local server before separate CLI access to the same instance. Retain the
whole stopped instance; an index backup omits artifacts. Existing exercise directories
are refused, so a new run cannot silently replace earlier evidence.

The application compares explicit declarations; it does not inspect your computer,
install software, edit settings or test live ports. Operator assertions do not prove
prerequisites, runtime compatibility, network availability or production readiness.
See the [application contract](../systems/environment-setup-workbench/docs/CONTRACT.md)
and [validation boundary](../systems/environment-setup-workbench/docs/VALIDATION.md).
