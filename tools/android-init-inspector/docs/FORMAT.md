# Literal init index format

The reader supports blank lines and comments whose first non-space/tab character
is `#`. Physical LF/CRLF lines are not joined. Any quote, backslash or `$` in a
noncomment line produces `NONLITERAL_STATEMENT` and resets section context, so a
partially understood header cannot capture later lines. Inline comments are not
stripped; use full-line comments in this subset. Tokens use ASCII spaces/tabs.

- `service NAME EXECUTABLE [ARG ...]` starts a service. NAME is 1–128 ASCII
  letters/digits/underscore/dot/hyphen. Executable/argument text is not validated
  for runtime correctness. Only argument count is reported, never raw argv.
- `on TRIGGER ...` starts an action; trigger text is not interpreted.
- `import PATH` records an unfollowed import and resets section context. Missing
  or extra operands still require review; no filesystem resolution occurs.
- Service options: `disabled`, `oneshot`, `override` with no operands;
  `class`, `user`, `group` with at least one operand; `critical` with 0–2
  operands; `reboot_on_failure` with one. These are observations, not validation
  of Android version-specific option grammar. Reboot-related markers are findings.
- `onrestart COMMAND ...` counts a restart command. Literal `reboot` is a finding;
  start/stop/restart/exec_start with one service name becomes a reference. Other
  restart commands are uninspected coverage.
- Action start/stop/restart/exec_start require exactly one supported name.
  `mount_all PATH [--early|--late]` is indexed without reading its target.

Duplicate declarations are never reduced to a winner, even with override.
References describe only selected declarations, not import order or effective
system state. Unsupported service/action statements and statements outside a
supported section appear in `coverage_issues`. Numeric flags, triggers and Linux
permissions are not validated. A source hash identifies exact selected bytes.

JSON schema version 1 includes inputs, services, actions, imports, references,
mount_all, findings, coverage_issues, status and details_included. IDs depend on
selected input and record order and are not stable across edits. No raw argv.
