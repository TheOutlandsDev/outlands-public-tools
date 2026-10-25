# Provenance and license scope

This release was developed from the owner's existing local phone dependency
analysis use case: walk declared dependencies, identify candidate libraries, and
record unresolved references. Local review covered the offline display closure
and runtime-string analyzers and the earlier PowerShell dependency helper.
Their original hashes and locations are recorded privately outside this source
tree; the originals remain unchanged. No device was contacted and no original
analysis script or firmware binary was executed for this release.

The new parser, bounded traversal, conservative resolver, report generation,
source checks, tests, documentation and synthetic example generator are freshly
written original release code, with AI assistance. No complete private helper,
fixed phone path, vendor/service seed list, proprietary binary, log, ADB workflow,
runtime implementation or device identifier was copied. Existing private source
snapshots and third-party materials receive no new license grant here. The old
vendor-first / first-filename-match decision is replaced with explicit ambiguity.

The owner's instruction authorizes public MIT publication of the reviewed original
tool. The included MIT notice covers this selected source, tests, documentation
and fictional examples. Authorship statements are not independent guarantees of
exclusive ownership of historical work. Python/OS/runtime components retain their
upstream terms and are installed separately. Inspected inputs and reports do not
become MIT simply because this tool reads or describes them.

## Format references

The parser implements a documented metadata subset using these primary ELF
format references, not copied third-party parser code:

- [ELF header](https://gabi.xinuos.com/elf/02-eheader.html)
- [Program headers and file-backed segments](https://gabi.xinuos.com/elf/07-pheader.html)
- [Dynamic linking and dynamic entries](https://gabi.xinuos.com/elf/08-dynamic.html)

Tests generate original ELF metadata using Python struct. The optional Linux
oracle compiles tiny authored C sources and compares with installed GNU readelf.
Compiler/binutils implementations and outputs are not distributed. The runtime
tool imports only the Python standard library and never invokes those commands.

Section tables, relocations, symbol/version binding, actual dynamic loading,
Android namespaces and platform loader behavior are deliberately outside the
supported subset. This tool does not approve blob redistribution or phone repairs.

## Runtime-hint extension (1.1.0)

The optional bounded ASCII scanner, token rules, report fields and tests are
freshly authored original MIT extension code, with AI assistance. The motivation
is the owner's private runtime-string analysis use case; the archived analyzer
was not copied into this module or re-licensed. No vendor/OEM implementation,
partition image, device-specific dependency seed list or phone configuration is
included. Tests append invented tokens to authored metadata fixtures. All source
inputs remain unchanged outside this publication tree.

The extension reads only selected/inventoried ELF handles and never invokes
`strings`, `readelf`, ADB, a shell or a native loader. Its observations are
explicitly separated from proven/declared metadata. Dynamic loading itself,
Android linker namespaces and actual firmware/configuration use remain outside
scope; observed text does not license the named software or establish its use.
