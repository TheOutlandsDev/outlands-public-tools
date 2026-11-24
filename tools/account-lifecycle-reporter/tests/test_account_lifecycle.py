from account_lifecycle import account_lifecycle_state


def test_account_lifecycle_uses_existing_security_fields() -> None:
    assert account_lifecycle_state({"active": False}) == "inactive"
    assert account_lifecycle_state(
        {
            "active": True,
            "password_change_required": True,
            "password_changed_at": None,
        }
    ) == "pending_first_sign_in"
    assert account_lifecycle_state(
        {
            "active": True,
            "password_change_required": True,
            "password_changed_at": "2025-02-15T12:00:00Z",
        }
    ) == "password_reset_required"
    assert account_lifecycle_state(
        {"active": True, "password_change_required": False}
    ) == "active"
