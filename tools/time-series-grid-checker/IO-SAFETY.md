# Checked local file boundaries

The library functions accept bounded supplied buffers. The CLIs read only explicit
file selections. No drive enumeration, environment expansion, manifest-path
following, network connection, service control or arbitrary input execution occurs.
Keep selected inputs and their parents trusted and quiescent while reading.

Every selected file must be an ordinary single-link file. POSIX traverses retained
ordinary directory descriptors, uses directory-relative stat/open with O_NOFOLLOW,
checks identities before/after reading, refuses nonregular files and limits bytes.
Output uses O_CREAT/O_EXCL/O_NOFOLLOW with requested mode 0600, fsync and sampled
readback metadata checks. Unsupported required descriptor APIs fail closed.

Windows uses the byte-identical public Environment Contract Checker native backend.
It retains ordinary ancestor/leaf handles, checks final native names/identities,
refuses reparse points and multi-link inputs, bounds reads and uses exclusive
new-file writes. Fully spelled ordinary local drive paths are required. UNC,
device, alternate-stream, drive-relative, short-name/observed alias and ambiguous
component spellings are refused. These tools read the primary stream only; they do
not enumerate alternate streams or certify the absence of other private data.

--out creates a new file under an existing private parent outside the source
checkout or recognized full collection source archive (outside this tool directory
when copied alone). No directories are
created by the checkers. Existing destinations are never replaced. Windows
permissions inherit from the selected parent; no ACL confidentiality guarantee is
provided. POSIX requests mode 0600 subject to the platform/filesystem. Neither
backend promises hostile-filesystem containment or an atomic multi-file snapshot.
Sampled metadata/hashes are not locks against privileged or adversarial mutation.

A failed/interrupted write can leave partial or complete-looking unconfirmed
output. It is retained; no pathname is deleted as recovery, and no retry reuses
that destination automatically. Inspect it privately and select a new destination.
Outputs, accepted values, identifiers, declared mappings, hashes and provenance
remain private. JSON escaping protects serialization, not anonymity. Shell stdout
redirection is controlled by the shell and does not inherit --out protections.
Structural validation does not sanitize real data or establish rights to share it.
