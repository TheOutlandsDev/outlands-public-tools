# Orchard handoff: make a failure reproducible

**Intake.** A reader must be able to follow a local setup document. The miniature
fictional handoff initially links to a missing guide.

**Decision.** Preserve the failing state in the procedure, then create the missing
guide and rerun the same checker. A passing link check is a prerequisite for
reading the handoff; it does not prove that the documented application works.

**Procedure.** The three-example runner creates `README.md` with a relative
`guide.md` link. Documentation Check must return non-PASS with exit 1. The runner
then creates the invented guide and requires PASS with exit 0. The observed
receipt records both outcomes instead of discarding the failure.

**Handoff.** Supply prerequisites, one useful workflow, expected results, the
actual platform/check outcome and known limitations. Retain a stop/recovery path.
For a browser application, separately check controls, focus, narrow screens,
errors, persistence and recovery before claiming interactive acceptance.

**Recovery and uncertainty.** Keep the generated workspace on failure. No checker
result approves publication of real project documents or proves every Markdown
construct, external link, accessibility need or runtime command.
