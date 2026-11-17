# Qualification contract

Pinned application interpreters: Python 3.12.16 and 3.15.2, Windows x64 and Ubuntu
x86-64. Each native job validates a freshly extracted deterministic source ZIP,
independently rebuilt ZIP/build manifest, a new venv with hash-locked binary wheels,
exact distributions, pip check and original source pins. The four native profiles
each require all 17 selected tests to execute and pass, with zero skips/failures/
errors and no unexpected warning. The release VALIDATION.json records actual jobs
and results; a committed workflow or this contract alone is not a passing result.

Checks cover original source/alias bytes and original check outputs; signed/zero
landscape and portrait synthetic oracles; unit conversion and retained pixel bias;
original no-display numeric parity; robust outliers/extremum boundaries; genuine
QC acceptance and forced fallback disclosure; blank, small, malformed, wrong-format
and oversized images; CLI exits, private-path error handling and input immutability;
six rendered plots and overwrite refusal; reparse checks and exclusive fixtures.
Native symlinks are additionally checked when host privileges allow creation; the
reparse refusal branch is always exercised. That is not a claim of Windows symlink
creation under a restricted account. No test method is silently skipped.

Only invented bar patterns are used; generated images and logs are private temporary
outputs, not shipped assets. The PNG generator's fixed shift/pitch is the numerical
oracle; cross-checks compare the unchanged original main and adapter. These checks
do not establish instrument calibration, production metrology, interactive picker
or desktop display operation, all image/geometry failure modes, hostile filesystem
containment, physical uncertainty or real-data accuracy. Agg rendering is qualified
separately from interactive desktop use. No original image/XML is needed or shipped.
