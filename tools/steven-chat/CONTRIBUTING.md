# Contributing to Steven Chat

Bug reports, practical suggestions and small documented changes are welcome in
the shared [OUTLANDS Public Tools repository](https://github.com/TheOutlandsDev/outlands-public-tools).
Use the [bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=steven_chat_bug.yml)
or [suggestion](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=steven_chat_suggestion.yml)
form with fictional inputs. Record whether an observation came from a unit test,
loopback fixture or real model/server run.

Run `python -B -m unittest discover -s tests -v` and `python -B source_check.py`
from this tool's directory. Regenerate the explicit source manifest only after
reviewing every intended source change; hashes prove selected bytes, not authorship
or application correctness. Keep generated sessions, downloaded models, virtual
environments and local reports outside the export.

Changes must retain the explicit connection opt-in, loopback-only endpoint
validation, inert output, bounded parsing and no-overwrite session behavior.
New backend/model integration needs primary documentation, a license review,
fixture tests and an honest runtime validation record. Do not add a bundled model
or silent network/model download. Preserve required upstream notices.

Contributions to original source are supplied under this folder's MIT license.
Do not submit code, data or conversations you lack permission to share. Security
or private-data reports should follow SECURITY.md instead of a public issue.
