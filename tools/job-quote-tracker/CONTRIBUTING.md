# Suggestions and contributions

Please use the collection's Job & Quote Tracker suggestion or bug form. Explain
your workflow, the problem, expected behavior, OS/Python version, and a small
fictional example. Improvements to accessibility, exports, quote line items,
filtering and clearer recovery instructions are welcome. Describe an idea before
undertaking a large change. Suggestions are welcome; no response time is promised.

Run the exact source gate and synthetic tests documented in README. For source
changes, review the explicit allowlist, then regenerate SOURCE-MANIFEST.json with
`python -B source_check.py --write-manifest`; generation does not itself approve
new source. Preserve the MIT notices. Submit only code you have rights to
contribute, and explain any new dependency and its license. Keep tests fictional.

Never upload a customer database/export/backup or real decision record. Use new
files in private scratch directories when reproducing filesystem problems.
