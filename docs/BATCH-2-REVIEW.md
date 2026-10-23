# OUTLANDS | Source review: inventory and XML inspection

This batch adds Source Inventory and XML Recipe Inspector as selected public source, alongside their synthetic tests and usage documentation. No real project inventory, recipe, image, generated report, original README containing input-derived conclusions, private audit record or source history is included.

## Changes and validation

Source Inventory retains its reviewed implementation and 18-test suite. XML Recipe Inspector adds fixed-code argument failures and a static help program name, so malformed command-line input cannot echo private argument values through default argparse diagnostics. Four regression methods cover unknown arguments, missing input, missing output and help text.

A fresh bounded offline run passed **18 Source Inventory methods and 34 XML Recipe Inspector methods**, with zero failures, errors or skips on Python 3.12.7/Linux. Tests used temporary fictional files and XML. Each isolated child ran with network system calls denied and a blocked-socket selfcheck; staged source/test bytes were unchanged by execution. This is software-behavior evidence for the checked fixtures, not production, hostile-filesystem or data-accuracy acceptance.

## Boundaries

- Inventory exclusions are convenience filters. CSV/JSON reports can expose relative names, hashes, sizes and timestamps; keep real reports private. Concurrent hostile ancestor replacement is outside the supported boundary.
- XML parsing rejects DTD/entity declarations, processing instructions and namespaces; input, depth, element/text and output ceilings are explicit. No referenced image, URL or command is opened by the inspector.
- XML geometry uses retained first-descendant PixelSize/X and PointProperty conventions. These may not fit another schema. There is no vendor validation, image processing or measurement-accuracy claim.
- File I/O requires the documented POSIX primitives. Windows support is not claimed. Failed writes can leave a new partial report directory; existing outputs are refused.

## Provenance and licensing

The owner reports personal work created with AI assistance. Public adaptations, documentation, the argument privacy correction and synthetic tests were AI-assisted. No required license or attribution notice was removed from the selected source. This bounded review does not independently establish exclusive authorship, novel invention or rights to surrounding private data.

Licensing remains unassigned. See [LICENSING.md](../LICENSING.md). This batch does not license other Programs folders or authorize publication of the private development repository. Document Builder and all other unselected material are outside this snapshot.
