# Qualification environment boundary

The original tools accept ordinary local native Windows volumes. Their guards
refuse the virtual NT volume names exposed by Windows Server Core containers.
A fresh NTFS scratch disk remains virtual from inside that container namespace.
The original tools, volume-name policy and all input checks remain unchanged.

Retained observations: [mapped directory](https://github.com/TheOutlandsDev/outlands-public-tools/actions/runs/41040375772)
and [new NTFS scratch disk](https://github.com/TheOutlandsDev/outlands-public-tools/actions/runs/41043006891).
Both storage selections returned `UNSAFE_PATH`; the bounded native probe reported
`virtual-nt-volume`. These are environment refusals, not passed qualification.

The previous hosted cleanup attempt stopped before runtime removal when its
inventory could not read a protected Defender directory. The
[failed job](https://github.com/TheOutlandsDev/outlands-public-tools/actions/runs/41050086961/job/124044883905)
records that result. Current CI uses the standard hosted Windows runner for the
bundled CMD and browser checks and compares its ZIP and receipt with the Linux
build. Publication is on hold.
