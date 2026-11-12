# Choose a private local workspace

Use an existing trusted local directory outside the unpacked source or any
public/synchronized checkout. The `D:\Private` examples in the usage guide are
fictional placeholders. On Windows use fully spelled ordinary drive paths;
on Ubuntu use canonical absolute local paths.

Create new child folders for downloaded wheels, an environment and test/output
work. Keep them separate from source. No administrator privileges, PowerShell
activation, execution-policy change, service installation or global package
update is needed. Use the chosen environment's Python executable directly.

Select only an authorized Markdown file. Its text and your title become DOCX
content. The tool does not anonymize text, establish source rights or prove
Windows ACL confidentiality. Source and output path strings are omitted from
the configured document core fields, but default-template metadata and ZIP
member times remain. Package inspection is not an anonymity guarantee.

Choose a new `.docx` filename in an existing private parent. Existing targets
are refused, and the builder does not create parents. A Windows write failure
may leave an empty, partial or complete but unconfirmed output. Preserve that
file for review; a retry must use a different new name. POSIX preserves its
original attempt to remove only its observed same-identity new file after a
failed write. Neither policy is a rollback transaction or race-proof sandbox.

Use trusted, stable filesystems and avoid concurrent mutation. The builder does
not block new files merely because their parent is a source directory; privacy
depends on your explicit workspace selection. Keep real inputs, generated
documents, wheelhouses, environments, native paths and diagnostics out of
public source inventories and release assets. Inspect content/metadata and
perform any necessary visual rendering review before sharing a real document.
