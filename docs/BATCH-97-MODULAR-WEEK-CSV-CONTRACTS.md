# Batch 97: ISO week and CSV profile contracts

Four independent MIT source tools add date-only ISO week aggregation, verification of supplied week labels, unmapped CSV column profiling, and pinned profile comparison. Each directory runs independently with Python 3.12/3.13 standard-library code and fictional examples.

The ISO week tools use canonical dates and do not infer timezones or convert timestamps. The CSV tools parse a bounded strict subset and report counts and lengths without cell values or type inference. Equal column profiles do not prove that underlying CSV records match; exact CSV hashes are reported separately.

The modules were freshly authored from generic concepts, following [Python's ISO calendar](https://docs.python.org/3.12/library/datetime.html) and [CSV reader](https://docs.python.org/3.12/library/csv.html). No original private source, dataset, business calendar, field map, or asset was selected. Source manifests pin each complete directory. Combined packaging and clearance of the original private families remain separate review work.
