# Private saved-report workspace

Keep saved badging text and generated comparisons outside the source checkout in
a private local directory you control. Select two distinct stable ordinary UTF-8
files and a new output directory with an existing absolute parent. Use authored
fictional text for this guide; keep actual captures and reports private.

The tool compares a documented subset of supplied text. It never opens APKs,
invokes AAPT2, captures metadata, installs apps or evaluates signatures/device
compatibility. Optional manual capture is a separate untested action documented
in CAPTURE.md; it is not required for the fictional walkthrough.

Default output omits raw package/library/value details; requested details can
expose them. Counts, opaque report-local identities and selected-text hashes can
still identify inputs, so output is not anonymized. Text hashes are not APK
hashes or evidence of capture completeness. Review reports before sharing them.

Unknown and ambiguous declarations remain held or covered, not inferred absent
or unchanged. Results do not establish a complete manifest diff, effective
runtime equivalence, app safety or compatibility. Path/handle checks and bounds
are best effort, not a hostile-filesystem transaction, atomic snapshot or hard
I/O deadline. A write failure may leave a partial new folder; resolve the cause
and select another fresh output. Unsigned manifests check consistency only.
