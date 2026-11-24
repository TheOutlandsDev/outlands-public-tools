from account_preset_workspace import (
    ACCOUNT_PRESET_CATALOG,
    ApplicationUserCreate,
    primary_workspace_path,
)


def test_account_presets_bind_access_roles_and_primary_workspaces() -> None:
    ptl = ApplicationUserCreate(
        username="new.ptl",
        display_name="New PTL",
        account_preset="flex_ptl",
    ).access_assignment()
    manager = ApplicationUserCreate(
        username="new.manager",
        display_name="New Manager",
        account_preset="flex_manager",
    ).access_assignment()
    engineer = ApplicationUserCreate(
        username="new.engineer",
        display_name="New Engineer",
        account_preset="flex_engineer",
    ).access_assignment()

    assert tuple(ACCOUNT_PRESET_CATALOG) == (
        "flex_operator",
        "flex_ptl",
        "flex_engineer",
        "flex_manager",
    )
    assert ptl.access_level == "power"
    assert ptl.functional_roles == ("ptl", "os_editor")
    assert manager.access_level == "power"
    assert manager.functional_roles == ("manager",)
    assert engineer.access_level == "power"
    assert engineer.functional_roles == ("engineer",)
    assert primary_workspace_path(ptl) == (
        "/labs/flex/ptl-suite"
    )
    assert primary_workspace_path(manager) == (
        "/labs/flex/ptl-suite"
    )
    assert primary_workspace_path(engineer) == (
        "/labs/flex/operator-work-center"
    )
