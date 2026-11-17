from __future__ import annotations

from unittest import TestCase

from starter.user_record import UserRecord, parse_user


class UserRecordEvalTests(TestCase):
    def test_parses_valid_user(self) -> None:
        user = parse_user({"id": "42", "email": " PERSON@Example.COM ", "active": "yes"})
        self.assertIsInstance(user, UserRecord)
        self.assertEqual(user.user_id, 42)
        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(user.active, True)

    def test_parses_false_values(self) -> None:
        self.assertFalse(parse_user({"id": "1", "email": "a@b.com", "active": "0"}).active)
        self.assertFalse(parse_user({"id": "1", "email": "a@b.com", "active": "NO"}).active)

    def test_rejects_bad_id(self) -> None:
        with self.assertRaises(ValueError):
            parse_user({"id": "-1", "email": "a@b.com", "active": "true"})

    def test_rejects_bad_email(self) -> None:
        with self.assertRaises(ValueError):
            parse_user({"id": "1", "email": "missing-at", "active": "true"})

    def test_rejects_bad_active(self) -> None:
        with self.assertRaises(ValueError):
            parse_user({"id": "1", "email": "a@b.com", "active": "maybe"})
