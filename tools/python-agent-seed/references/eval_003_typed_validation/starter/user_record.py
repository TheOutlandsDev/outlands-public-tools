"""Separate typed reference repair with the task's deliberately narrow rules."""
from dataclasses import dataclass

@dataclass(frozen=True)
class UserRecord:
    user_id: int
    email: str
    active: bool

def parse_user(row: dict[str, str]) -> UserRecord:
    raw_id = row.get('id', '').strip()
    email = row.get('email', '').strip().lower()
    active = row.get('active', 'true').strip().lower()
    if not raw_id.isdecimal():
        raise ValueError('ID must be decimal non-negative text')
    if email.count('@') != 1 or not all(email.split('@')):
        raise ValueError('Email must have one @ and nonempty parts')
    if active not in ('true', 'false', '1', '0', 'yes', 'no'):
        raise ValueError('Active value is not supported')
    return UserRecord(int(raw_id), email, active in ('true', '1', 'yes'))
