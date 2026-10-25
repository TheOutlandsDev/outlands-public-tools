# Contributing

Suggestions, small fictional reproductions and focused coverage improvements are
welcome. Use the [bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=svg_content_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=svg_content_suggestion.yml).
Include OS, Python/Expat versions, command, status and expected supported behavior.
Share only generated examples you have rights to contribute; no actual artwork,
private references, credentials, portfolio content or unredacted reports.

Preserve the static-only contract. Do not add rendering, network fetching,
implicit local reference access, DTD resolution or a parser-security bypass.
Additional CSS/SVG syntax needs documented coverage, resource limits, malformed
fixtures and explicit uncertainty when unsupported. A source marker is not an
executable-behavior verdict. Keep reports inert, fresh-only and privacy-aware.

Run `python -B -W error -m unittest discover -s tests -v` and
`python -B source_check.py` with the required updated Expat. Never convert a
failed bound or parser guard into a partial successful report. Contributions
to this original module are made under its MIT license; all third-party rights
and notices remain intact.
