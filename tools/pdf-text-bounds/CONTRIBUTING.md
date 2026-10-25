# Contributing

Bug reports, useful coverage improvements and suggestions are welcome through
the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=pdf_bounds_bug.yml)
and [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=pdf_bounds_suggestion.yml).
Use original minimal generated PDFs. Do not attach actual private documents,
extracted text, credentials, private paths or proprietary artwork.

Run the pinned dependency installation, complete unittest suite and source gate.
Coordinate changes need independent expected geometry, nonzero/rotated/cropped
fixtures and updated format documentation. Parser failures and limits must remain
incomplete failures; never silently return a successful subset. Keep runtime
inspection offline and read-only. New extraction/rendering/repair features would
need a separate scope and privacy review.

Dependency updates require license/notices, installed-pin and current advisory
checks, plus actual parser tests on Windows/Ubuntu and supported Python versions.
Maintain the isolated worker/time/output boundaries. Audit hooks are not an OS
sandbox and must not be described as one. Report counts and platform skips
honestly. Original contributions to this module are MIT licensed; third-party
rights and notices remain applicable.
