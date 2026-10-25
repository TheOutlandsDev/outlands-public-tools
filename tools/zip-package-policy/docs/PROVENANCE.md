# Provenance and license scope

This public tool was freshly implemented in 2026 for the OUTLANDS Public Tools
collection, inspired by the owner's local package-checking workflow: compare an
expected archive digest/size and member list, then inspect selected text markers.
The local workflow was specific to a private package. Its package paths, digest,
payload names, private contents and hardware commands are not part of this tool.

All source, documentation and generated tests/examples in this directory are
original contributions released under the included MIT license. The example
Orchard utility, its INI file and its README are fictional generated fixtures.
No downloaded ZIP, game asset, firmware image, proprietary implementation,
installed executable, personal configuration or original private report is
distributed. No third-party source or PowerShell module is bundled.

The checker uses PowerShell 7.2 or newer and .NET platform APIs. Those runtimes remain under
their own licenses; they are prerequisites rather than relicensed source. The
MIT license grants rights only to this original tool and does not grant rights
to the archives a user chooses to inspect.

Future changes must preserve this boundary. Reproductions should be generated
minimal examples whose author can grant redistribution rights. Real package
hashes, paths or reports need separate review before public inclusion.
