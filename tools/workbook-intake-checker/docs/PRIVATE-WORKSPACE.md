# Private mapped CSV and workbook previews

Select an ordinary CSV or supported XLSX source and a caller-authored mapping in a trusted private workspace. Outputs contain accepted typed values, identities, source/mapping hashes and row provenance by default. Rejected/conflicting values are withheld, but unrelated valid records can remain visible while the batch requires review. Neither hashes nor rejection handling anonymize a real input or authorize sharing.

Every workbook sheet must pass the supported structural checks, including unselected sheets. This is a deliberately limited stored-cell subset: no formula evaluation, macros, Office process, external-resource following, visible layout or general Excel compatibility is qualified. Styles do not turn stored numeric literals into displayed date/percentage semantics. Input ZIP parts are read in memory; verified source-ZIP extraction during packaging is separate.

Typed decimal previews are qualified with the selected C Decimal implementation and pristine default context (precision 28). Caller-mutated contexts are outside that envelope; context independence is not claimed. The maximum accepted decimal syntax fits the qualified precision. No normalization into business policy or external import is performed.

Use stable ordinary inputs, fully spelled paths and a fresh external output name under a trusted existing parent. Linked/multilink paths and name reuse are refused. The Windows writer uses create-new and open-reparse-point safeguards, including existing dangling leaves. Failed writes may retain unconfirmed partial output. Windows ACLs inherit from the parent. Sampled metadata checks and cooperative bounds do not establish an atomic snapshot, hostile-writer containment or hardware durability.

Only generic source and invented examples are published. Original workbooks, real records, generated reports, interpreters, credentials and raw evidence remain private. Obtain Python separately; its components retain their upstream licenses.
