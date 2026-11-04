# Batch 98: Modular JSON and XML structure tools

Four independent MIT source tools inspect bounded supplied text offline:

| Tool | Exact boundary |
| --- | --- |
| [JSON Structure Profiler](../tools/json-structure-profiler/README.md) | Counts value types by normalized object-key and array-item path; no scalar values. |
| [JSON Structure Revision Comparator](../tools/json-structure-revision-comparator/README.md) | Reprofiles two pinned documents and reports structural count changes; equal shapes do not prove equal values. |
| [XML Structure Profiler](../tools/xml-structure-profiler/README.md) | Counts expanded element paths, attribute names, direct nonblank text presence and direct children; no text or attribute values. |
| [XML Structure Revision Comparator](../tools/xml-structure-revision-comparator/README.md) | Reprofiles two pinned documents and reports element-shape changes; equal shapes do not prove equal text. |

These are fresh generic contracts informed by private **filename and hash metadata only**. No original private source, XML, JSON, configuration, dataset or instance was selected. The public shared file-safety helpers are MIT source. These modules do not clear any original private application family. They neither fetch URLs nor change target documents. The checked examples are invented. Keep real inputs and reports private because names, structure and hashes can disclose information.

The existing `configuration-contract-checker` validates explicit settings, and the XML recipe/workflow tools inspect their own declared subsets. These tools profile raw bounded structure without application-specific schemas. Combined distribution packaging is deferred.
