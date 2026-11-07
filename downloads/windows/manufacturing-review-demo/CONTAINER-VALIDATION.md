# Qualification environment boundary

The original tools accept ordinary local native Windows volumes. Their guards
refuse the virtual NT volume names exposed by Windows Server Core containers.
A fresh NTFS scratch disk remains virtual from inside that container namespace.
The original tools, volume-name policy and all input checks remain unchanged.

Retained observations: [mapped directory](https://github.com/TheOutlandsDev/outlands-public-tools/actions/runs/41040375772)
and [new NTFS scratch disk](https://github.com/TheOutlandsDev/outlands-public-tools/actions/runs/41043006891).
Both storage selections returned `UNSAFE_PATH`; the bounded native probe reported
`virtual-nt-volume`. These are environment refusals, not passed qualification.

The release gate uses a fresh full hosted Windows runner instead. Before bundle
extraction it inventories and removes pre-existing Python interpreter/launcher
executables from the explicitly scanned installation roots, requires a complete
rescan with zero remaining matches, checks command lookup and callable registered
Python, then executes the actual bundled CMD checks using the included interpreter.
It removes no user data and is restricted to ephemeral GitHub-hosted runners.
This is a prepared Windows host, not a claim of a pristine OS installation or
absence of every Python-related library file. Network access remains available
to the runner. The separate browser job records the actual offline report page.
