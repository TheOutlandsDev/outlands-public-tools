# Validation record

The publication checks use generated temporary text, never real device inputs.
Run `python -B -W error -m unittest discover -s tests -v` and
`python -B source_check.py` from the module folder to reproduce locally.

Coverage includes supported parsing and explicit unsupported syntax, the actual
CLI with generated examples, default private-field omission, stable source
reads, immutable inputs, strict encoding/bounds, fresh report outputs, HTML
escaping and manifest byte/hash verification. Semantic fixtures are specific to
this parser; shared filesystem/report tests are identical first-party code in
each standalone module.

The Android configuration batch CI matrix is Ubuntu Python 3.12/3.13 and Windows
Python 3.13/3.14. Every matrix job verifies all three source inventories and runs
all three suites with warnings treated as errors. Windows alternate-stream
syntax is tested only on Windows; POSIX FIFOs only where supported. Symlink and
hardlink creation tests skip only if the host cannot create the required link.
Skipped platform mechanisms are not claimed as tested on that host.

Source gates inspect explicit UTF-8 source-only allowlists and SHA-256 manifests;
they do not prove authorship or provide signed authenticity. Parser tests do not
prove correct boot/build/mount behavior. No external resource is followed and no
real target system is modified. Review coverage issues before interpreting any
report. CI results for the source commit are visible under repository Actions.
