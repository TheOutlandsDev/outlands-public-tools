# Input and output safety

The caller selects one bounded local JSON input. The public checked-file helper refuses linked/reparse inputs, duplicate JSON keys, floating point values, excessive size or depth, and unsafe output paths. Output is stdout unless `--out` selects a new private file outside the source tree. No SQL, network, browser, model, telemetry, or chart renderer is invoked. Real identifiers and values may be sensitive; keep real inputs and reports private.
