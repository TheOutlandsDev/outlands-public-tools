# Contributing

Suggestions and bug reports are welcome through the module's
[bug](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=zip_policy_bug.yml)
and [suggestion](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=zip_policy_suggestion.yml)
forms. Explain the use case, OS, PowerShell version and expected result. Include a
small generated example rather than a private archive or report. Do not disclose
tokens, private keys, personal paths, proprietary assets or third-party payloads.

Keep changes within the read-only checker scope. Do not add extraction,
installation, command execution, device operations or implicit network access.
Document supported ZIP behavior and bounds; never remove a bound to force a test
to pass. Add a generated test for meaningful parser/behavior changes and run the
suite on PowerShell 7.2 or newer. New dependencies require license and security review.

Submit only code and examples you can license under MIT. Platform/runtime
licenses and the rights to user inputs remain separate.
