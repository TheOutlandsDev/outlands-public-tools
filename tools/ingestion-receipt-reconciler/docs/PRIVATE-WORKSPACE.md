# Private four-selection receipt reconciliation

Select four stable ordinary files explicitly: receipt JSON, CSV/supported XLSX source, mapping JSON and preview JSON. Each role is bounded to 4 MiB. The receipt selects source format and XLSX sheet; no path is followed from its body. Generic run_core manifest limits belong to separate preserved/tested helpers and are not a receipt CLI pipeline. Four sequential bounded reads are not an atomic snapshot.

The reconciler actually reruns the preserved public intake parser and compares source/mapping/preview raw pins, canonical typed preview contents and observed row counts. Typed JSON comparison distinguishes booleans from integers. Rejections/conflicts/empty accepted sets or any mismatch withhold readiness while recomputed counts and fixed issues remain. A harmless preview reserialization can match canonical content when its raw pin is updated; supplied raw and recomputed canonical pins remain distinct evidence.

Recomputation does not authenticate a receipt, establish source authority, inspect a store, prove exactly-once execution, authorize an import or qualify a production workflow. Reports expose receipt ID, counts, issues and fingerprints; keep real files/reports private. Hashes and omitted body values do not anonymize them.

The bounded XLSX stored-cell subset refuses formulas, macros, external relationships and unsupported structures, including rejected content in unselected sheets. It does not evaluate formulas or certify visible layout. Decimal conversion is qualified with selected C Decimal and pristine default context (precision 28); caller-mutated contexts are outside the envelope. Complete pinned SDK identity does not establish independent component rebuilds.

Use fully spelled stable ordinary paths and trusted quiescent parents. Native linked/multilink inputs and source-tree outputs are refused. Output requires a fresh external name under an existing parent. Windows CREATE_NEW/OPEN_REPARSE_POINT refuses existing and dangling leaves. Failed writes may retain unconfirmed partial output; preserve it and choose a new name. Parent ACLs are inherited. Cooperative limits and sampled metadata do not establish OS isolation, hostile-writer containment, atomic snapshots, rollback or hardware durability.

Only generic source, a fictional workbook generator and four invented text/JSON fixtures are published. Real files, generated workbooks/reports, SDKs, credentials and raw validation logs remain local. Obtain Python separately.
