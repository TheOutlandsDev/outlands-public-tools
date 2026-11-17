# Refactor Example: Explicit validation

## Before

```python
def normalize_user(row):
    return {"id": int(row["id"]), "email": row["email"].strip().lower()}
```

## After

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserRecord:
    user_id: int
    email: str


def normalize_user(row: dict[str, str]) -> UserRecord:
    raw_id = row.get("id", "").strip()
    raw_email = row.get("email", "").strip().lower()

    if not raw_id.isdecimal():
        raise ValueError("user id must be a non-negative integer")
    if "@" not in raw_email:
        raise ValueError("email is invalid")

    return UserRecord(user_id=int(raw_id), email=raw_email)
```

## Why the second version is better

- Defines a typed result.
- Validates missing and malformed data.
- Uses explicit error messages.
- Avoids returning loosely structured data for a domain concept.
