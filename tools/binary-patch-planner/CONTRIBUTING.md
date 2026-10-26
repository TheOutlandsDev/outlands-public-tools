# Contributing

Bug reports, workflow/usability feedback and format suggestions are welcome
through the [public issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's bug or suggestion form. Include OS/Python version, source
commit, exact commands with private paths removed, expected behavior and a small
**fictional** reproduction you have rights to publish. No live binaries, game
assets, firmware, private recipes, credentials or unredacted reports.

Keep default preview and explicit separate-output semantics. Do not weaken
source hash/byte, bounds, link, alias or exclusive-create checks to make an input
pass. New formats and size increases require a separately reviewed resource and
privacy design. Generated fixtures should cover the intended behavior and failure
mode, not simply mirror implementation branches. Preserve MIT and other notices.

Run the documented tests and `python -B source_check.py`. After reviewing a
deliberate source change, update the exact inventory with
`python -B source_check.py --write-manifest` and rerun both checks. Unsigned
manifests detect drift; they are not proof of authenticity or secret absence.
