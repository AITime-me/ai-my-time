import pytest
from pydantic import ValidationError

from app.api.routes.admin_ui import _PAGE
from app.schemas.admin import AdminLeadList


def test_admin_lead_list_requires_a_bounded_limit() -> None:
    assert AdminLeadList(items=[], limit=50).limit == 50

    with pytest.raises(ValidationError):
        AdminLeadList(items=[], limit=101)


def test_admin_person_detail_renders_website_attribution_fields() -> None:
    assert "p.source_label||source(p.source)" in _PAGE
    assert "p.entry_code||'—'" in _PAGE
    assert "intent(p.intent)" in _PAGE
