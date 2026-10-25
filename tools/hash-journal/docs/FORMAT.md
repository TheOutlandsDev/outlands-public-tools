# Hash Journal version 1

The file is strict UTF-8 without a BOM. Every record is a single JSON object,
followed by LF (`0a`). A final LF is required. Raw CR, blank lines, invalid UTF-8,
invalid JSON, excessive nesting, duplicate properties and extra properties fail
verification. JSON whitespace within a line and member order are not hash inputs.

Exactly these properties occur once per object:

| Property | Required value |
| --- | --- |
| `schema` | Integer JSON token `1`; floating/exponent/boolean syntax is refused. |
| `sequence` | Integer token, contiguous from 1, at most 10,000. |
| `previous` | 64 lowercase hexadecimal characters; record one uses 64 zeros. |
| `text` | Nonblank string, at most 8,192 bytes when strictly UTF-8 encoded. |
| `hash` | 64 lowercase hexadecimal characters matching the formula below. |

The exact hash message is the UTF-8 encoding of these concatenated strings:

```text
"outlands-hash-journal-v1\n"
+ decimal_sequence_without_sign_or_leading_zeroes
+ "\n"
+ previous_lowercase_hex
+ "\n"
+ exact_decoded_text
```

Compute SHA-256 and encode its 32 bytes as 64 lowercase hex characters. The
domain, sequence and previous hash have fixed, unambiguous boundaries; text is
the remainder. Text can contain JSON-escaped newline/CR/quote characters. Text
uses no Unicode normalization. JSON escaping/member order can change without
changing the decoded text or its computed hash. This is this tool's format,
not a claim to implement JCS or another standardized canonical JSON protocol.

The next record's `previous` must equal the preceding verified hash. For the
fictional text `Fictional build prepared.`, sequence one has hash:

```text
66a82dd6cfc9760a7b9d754525fe693e9d63ca60e427e3d1d2bd25a4c61c398e
```

That golden value was independently calculated with Python's SHA-256 function
and checked by the C# fixture harness.

The whole-file limit is 1,048,576 bytes, including line terminators. A line can
contain at most 65,536 bytes excluding its LF. Limits are independent and apply
together. The encoder validates all selected records and constructs the bounded
bytes before opening a new output; fresh output uses LF regardless of platform.

## Anchors and what verification means

`VALID_UNANCHORED` means the selected chain's internal sequence, links, hashes
and format passed. It does not identify an authorized writer. A complete-record
tail can be removed and leave a valid prefix. A whole chain can be replaced and
rehashed. A trusted expected count detects only a count mismatch.

`VALID_HEAD_MATCHED` additionally means the resulting final hash matched the
explicit expected head. Keep that head in a separately trusted place. Supplying
a head read from the same untrusted file provides no independent protection.
A matching head is not a signature, witness, timestamp, factual-event guarantee
or proof that data was continuously retained. No chain-only check detects every
filesystem attack or establishes access control.

## Files and failures

`create` creates record one in a new file. `append` verifies a selected file,
builds the next record and creates a different new version. No in-place append,
overwrite, automatic folder creation or deletion exists. An error after output
creation can leave a partial fresh file; error code
`OUTPUT_WRITE_FAILED_PARTIAL_POSSIBLE` makes that possibility explicit.

Observed links/reparse components, directories and unsupported Windows paths
are refused. Input size and modification time are checked around the bounded
read. These are detection checks on trusted quiescent paths, not descriptor-
relative containment or an atomic snapshot against hostile concurrent writers.
Unix special files of zero reported length are refused before opening; the
supported input remains an ordinary selected regular file, not arbitrary device
nodes or virtual filesystem records.
