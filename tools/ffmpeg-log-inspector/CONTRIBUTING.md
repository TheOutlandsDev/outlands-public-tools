# Contributing

Suggestions and small fictional reproductions are welcome through the
[bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=ffmpeg_log_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=ffmpeg_log_suggestion.yml).
Include OS, PowerShell version, source commit, command, exit status and expected
supported observation. Do not attach actual capture logs, private media names,
URLs with credentials, recordings or copyrighted input artifacts.

New log support needs a documented grammar, bounded parsing and synthetic
fixtures covering malformed/unavailable/ambiguous data. Preserve separation of
observations from recording, device-health and process-completion conclusions.
Do not infer time units from a key name without a tested supported contract.
Keep unknown/raw text out of reports and retain visible coverage limits.

Run the complete CLI harness and source gate described in [README.md](README.md).
Use an explicit new private WorkRoot, never a real capture folder. Keep original
MIT notices and third-party rights intact. Original contributions to this module
are offered under its MIT license; no input log or external binary is relicensed.
