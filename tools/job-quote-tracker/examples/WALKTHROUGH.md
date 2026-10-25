# A fictional job, from intake to recovery

Run from `tools/job-quote-tracker`. Work in a private scratch folder and supply
new output names if you repeat this walkthrough. The included examples contain
only fictional data.

1. `python tracker.py init practice.sqlite`
2. `python tracker.py new practice.sqlite --input examples/job.json`
3. Copy the returned `id` (`job-` followed by 16 hex characters). Replace JOB_ID
   in each next command with that exact ID. The new record's version is 1.
4. `python tracker.py quote practice.sqlite JOB_ID --expected-version 1 --input examples/quote.json`
   Expected: quoted, revision 1, amount 125.10 USD, version 2.
5. `python tracker.py decision practice.sqlite JOB_ID --expected-version 2 --state approved --reference "Fictional confirmation for practice only"`
   Expected: approved, one recorded decision, version 3.
6. `python tracker.py status practice.sqlite JOB_ID --expected-version 3 --state scheduled --date 2026-12-01`
   Expected: scheduled on December 1, version 4.
7. `python tracker.py quote practice.sqlite JOB_ID --expected-version 4 --input examples/quote.json`
   Expected: quoted, revision 2, version 5, blank scheduled date. Revision 1's
   approval remains in history; revision 2 has no recorded decision. Scheduling
   again will fail until you record an approval for revision 2.
8. `python tracker.py backup practice.sqlite practice-backup`
9. `python tracker.py verify-backup practice-backup`
10. `python tracker.py restore practice-backup practice-recovered.sqlite`
11. `python tracker.py show practice-recovered.sqlite JOB_ID`
    Compare the two revisions and recorded decision with step 7.
12. `python tracker.py export practice-recovered.sqlite practice-report`
    Open `practice-report/index.html`. Review `jobs.csv` and `data.json`.

Reports are viewable records, not restorable backups. Keep the complete two-file
backup folder for recovery. Reusing an existing store/output name is refused.
