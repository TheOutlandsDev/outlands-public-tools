# Security and privacy boundaries

This is a bounded offline text inspector for explicit stable regular files and
trusted output parents. It is not a filesystem sandbox, secret scanner, compiler,
build validator, module security analysis or authoritative tree inventory.
No network, subprocess, source-tree walk, include execution, build or device
operation is implemented in the inspector.

Default reports omit literal names and discarded source fields, but hashes,
sizes, line positions and structure can still identify inputs. Optional details
add names/kinds. Keep actual build files and identifying reports private.
Do not put sensitive reproductions or proprietary source in public issues.

Inputs are opened read-only. Reports are created exclusively in a new directory;
an I/O failure can leave a partial new output. Ordinary file changes and linked
paths are refused, without claiming an atomic snapshot against a malicious
filesystem owner. Use a fresh destination after resolving a failed write.

For a suspected defect, share a minimal invented input and fixed error code in
the [issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose)
without sensitive details. Read the collection's root security guidance for
any available private reporting route. Source/report manifests are unsigned
consistency evidence, not cryptographic proof of origin or authenticity.
