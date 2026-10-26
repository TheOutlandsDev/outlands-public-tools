# Literal permission manifest grammar

Supported UTF-8 text shares the byte/file/line limits documented in README.
Blank/full-line # comments are ignored. ASCII spaces/tabs delimit fields; inline
comments, quoting and escaping are unsupported. First field is a relative path
of forward-slash ASCII letter/digit/dot/underscore/hyphen/plus/@/equals components,
<=512 characters with no empty/dot/parent component. Paths compare exactly,
case-sensitively, without filesystem lookup, case folding or normalization.

UID/GID are 1–10 decimal digits representing 0..2^32-1; leading zeroes normalize
numerically. Mode is 1–4 octal digits normalized to four digits (0000..7777).
File-type-bit modes (e.g. 100644), symbolic modes and names are unsupported.
These checks describe the subset, not every build tool's accepted grammar.

Optional fields are selabel=CONTEXT and capabilities=0xHEX, each at most once.
Context is <=512 ASCII literal user:role:type:level/category text in the stated
character subset; no policy or category-set evaluation occurs. Hex is 1–16
digits after lowercase 0x; it normalizes to a lowercase hex string. Missing
optional fields are null/unspecified, distinct from an explicit zero or a label.
Unknown/repeated/invalid fields hold the entire known path as unsupported.

Unique supported paths compare UID, GID, mode_octal, selabel and capabilities.
Duplicate paths on either side are held rather than paired, even if identical.
Known paths with unsupported metadata are held, never invented as removals.
Unknown path syntax records an unidentified location; unmatched identities on
the opposite side are held because their absence cannot be established within
this parser's scope. Unique matched supported changes remain visible alongside
coverage. Literal path renames are removal/addition only where supported.

No binary config, target-files archive, filesystem, path target, symlink, user
database or SELinux policy is opened. No permission/ownership/label/capability is
applied. Effective access, source provenance and deployment safety are outside
scope; a mode/mask change is a declared difference, not an automatic risk score.

Schema version 1 shares records, changes, held_identities, unidentified_rows,
comparison_counts/scope and findings/coverage/status with the property diff.
Default records omit paths/values. Details opt-in adds declared_identity and
supported normalized fields; unsupported raw fields are never embedded.
