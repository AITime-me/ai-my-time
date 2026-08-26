import pytest
from pydantic import ValidationError

from app.schemas.admin import AdminLeadList


def test_admin_lead_list_requires_a_bounded_limit() -> None:
    assert AdminLeadList(items=[], limit=50).limit == 50

    with pytest.raises(ValidationError):
        AdminLeadList(items=[], limit=101)
