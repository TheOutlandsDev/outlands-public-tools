# Five-minute fictional manufacturing review

Use Python 3.12/3.13 and the **complete Toolkit 0.8.0 source ZIP**. Python is
supplied separately; this source exercise does not use a bundled Windows app.
From the extracted root, choose a new absolute private directory beneath an
existing ordinary parent outside the package:

```text
python -B workshops/manufacturing_review.py --workspace NEW_ABSOLUTE_PRIVATE_DIRECTORY
```

The runner invokes four unchanged public Python CLIs twelve times. Inputs are
invented resource/task declarations, ordinal process events and whole-piece
movements. It retains every input/report, including four expected exit-1
REVIEW_REQUIRED outcomes, then independently checks arithmetic, input pins,
shared resource pins, duplicate accounting and report hashes. Reusing an existing
workspace is refused without changing its files. A failed run remains for review.

1. **Inspect eligibility.** Two of three initial proposals are individually
   eligible; station A lacks the declared calibration capability. A new proposal
   names station B, producing three individually eligible tasks. This does not
   check combined reservation capacity or certify real qualifications.
2. **Find the overlap.** Those individually eligible tasks still reserve three
   units against capacity two during `[3,6)`. A separately authored proposed
   revision moves task B's start to 6. Peak use becomes two; an end and a start at
   the same ordinal do not overlap. No task or reservation is actually applied.
3. **Explain the delay.** A missing finish event withholds totals. The complete
   supplied run has 12 elapsed ticks: 9 active and 3 held. An identical repeated
   event is counted once. Ticks are declared ordinals, not a measured live clock
   or a physical production rate; this is not a wall-clock batch makespan.
4. **Reconcile quantities.** Opening 20 + received 5 - dispatched 3 - declared
   adjustment 1 = closing 21. Stock is 17 and WIP is 4. Declaring WIP as 5 retains
   a mismatch of one; the corrected declaration balances. Repeating the same
   movement identity does not inflate the total. No inventory is updated or
   intermediate stock level or physical count independently verified.

The final `observed-results.json` records twelve command checks, four expected
review outcomes and `operator_review: REQUIRED`. PASS means the authored exercise
matched its expected results. It does not approve a plan, establish a repair,
authorize work, validate source authority or grant permission to publish data.
Each input/report pin can be independently recomputed from the private files.

The four tools keep separate contracts. Only the authored task-to-reservation
mapping joins their fictional inputs, and both resource hashes must agree.
Original inputs and all earlier diagnostic reports remain unchanged. There is
no scheduler, workforce decision, reservation lock, employer system, live probe,
automatic redaction, or real manufacturing action in this demonstration.
