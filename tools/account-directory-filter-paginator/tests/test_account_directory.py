from pathlib import Path

from account_directory_filter import DirectoryFilters, filter_directory, read_snapshot


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "directory.json"


def test_directory_scope_options_and_pending_first_sign_in() -> None:
    directory = read_snapshot(EXAMPLE)
    pending_directory = filter_directory(
        directory, DirectoryFilters(account_status="pending-first-sign-in")
    )
    options = pending_directory.lab_scope_options
    assert ("", "Any lab scope") in options
    assert ("all", "All labs") in options
    assert sum(label == "All labs" for _, label in options) == 1

    assert pending_directory.status_label == "Pending first sign-in"
    names = {account.display_name for account in pending_directory.accounts}
    assert "New Operator" in names
    assert "New PTL" in names
