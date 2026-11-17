# Python 3.12.7 Coding Doctrine

## Default style

Write Python that is:

- Simple.
- Typed.
- Testable.
- Secure by default.
- Easy to review in a pull request.

## Language rules

- Target Python 3.12.7 unless a project config says otherwise.
- Do not use `distutils`; it is removed in Python 3.12.
- Use f-strings for readable formatting when appropriate.
- Use `pathlib.Path` for filesystem paths.
- Use `dataclasses.dataclass` for simple structured domain objects when appropriate.
- Use `enum.Enum` or `StrEnum` for constrained symbolic values when useful.
- Use context managers for resources.
- Use `Decimal` for money-like decimal calculations.
- Use `zoneinfo` for time zones instead of adding heavy dependencies by default.

## Typing rules

- Public functions and methods should have parameter and return annotations.
- Prefer precise types over `Any`.
- Use `Protocol` for structural interfaces.
- Use `TypedDict` or dataclasses for structured records.
- Use `Self` for fluent APIs when appropriate.
- Use Python 3.12 generic syntax only when the target project allows it.
- Do not overcomplicate simple code with excessive type machinery.

## Testing rules

- Behavior changes require tests.
- Cover success paths, boundary cases, and failure paths.
- Use temporary directories for filesystem tests.
- Avoid tests that depend on wall-clock time, network access, or local machine state unless explicitly required.

## Security rules

- Do not use `eval` or `exec` on untrusted input.
- Do not deserialize untrusted data with `pickle`, `shelve`, or equivalent unsafe serializers.
- Do not use `subprocess` with `shell=True` unless the need is explicit and justified.
- Do not log secrets or sensitive identifiers.
- Validate external input at trust boundaries.
- Prefer allowlists over blocklists for validation.
- Use `secrets`, not `random`, for security-sensitive randomness.

## Error-handling rules

- Catch specific exceptions.
- Do not swallow exceptions silently.
- Preserve useful error context.
- Raise domain-specific exceptions when that improves caller behavior.
- Avoid returning `None` for error states unless the API clearly documents it.

## Logging rules

- Libraries should define loggers with `logging.getLogger(__name__)`.
- Application entry points configure logging.
- Logs should help operators debug without leaking secrets or sensitive data.
