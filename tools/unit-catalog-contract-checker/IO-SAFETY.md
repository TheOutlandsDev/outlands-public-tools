# Input and output safety

The checked public helper limits input to 4 MiB, rejects duplicate JSON keys, floats, excessive depth and invalid paths, and writes only new files outside the source tree. The tool does not read or update target systems. Reports may expose supplied IDs, catalog labels, exact factors and converted values; keep private inputs and their reports private. Hashes are not anonymization. Failed output may be partial and must be reviewed.
