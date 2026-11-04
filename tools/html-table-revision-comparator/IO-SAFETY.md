# Input and output safety

The caller selects one bounded local strict JSON input. The public checked-file helper refuses linked/reparse inputs, duplicate JSON keys, floats, excessive size/depth and unsafe output paths. Output is stdout unless `--out` writes one new private file outside the source tree. No network, browser, SQL, task execution or target mutation is used. Supplied text, IDs and hashes may be sensitive.
