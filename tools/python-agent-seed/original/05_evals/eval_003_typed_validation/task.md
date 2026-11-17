# Eval 003: Typed validation

## Task

Improve `starter/user_record.py` so that `parse_user` returns a typed immutable object and validates the input.

## Requirements

- Create a frozen dataclass named `UserRecord`.
- Fields: `user_id: int`, `email: str`, `active: bool`.
- Accept input rows as `dict[str, str]`.
- Valid `id` is decimal text representing a non-negative integer.
- Valid email contains exactly one `@` and has non-empty local/domain parts.
- Valid active values: `true`, `false`, `1`, `0`, `yes`, `no`, case-insensitive.
- Raise `ValueError` for invalid input.
- Keep the public function name `parse_user`.
