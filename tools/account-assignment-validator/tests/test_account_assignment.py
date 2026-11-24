import pytest
from pydantic import ValidationError

from account_assignment import UserAccessUpdate


def test_assignment_contract_rejects_invalid_role_level_combinations() -> None:
    with pytest.raises(ValidationError):
        UserAccessUpdate(
            access_level="standard",
            functional_roles=("ptl",),
            lab_scopes=("flex",),
        )
    with pytest.raises(ValidationError):
        UserAccessUpdate(
            access_level="standard",
            functional_roles=("engineer",),
            lab_scopes=("flex",),
        )
    with pytest.raises(ValidationError):
        UserAccessUpdate(
            access_level="developer",
            functional_roles=(),
            lab_scopes=("flex",),
        )
    with pytest.raises(ValidationError):
        UserAccessUpdate(
            access_level="power",
            functional_roles=("manager",),
            lab_scopes=("all",),
        )
