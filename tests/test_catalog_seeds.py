import pytest

from app.db.models.catalogs import Country, ResultType
from app.db.session import SessionLocal


@pytest.mark.integration
def test_catalog_seed_country_exists():
    db = SessionLocal()
    try:
        country = db.query(Country).filter_by(iso_code="COL").one_or_none()
        assert country is not None
    finally:
        db.close()


@pytest.mark.integration
def test_result_type_scrutiny_exists():
    db = SessionLocal()
    try:
        result_type = db.query(ResultType).filter_by(code="SCRUTINY").one_or_none()
        assert result_type is not None
    finally:
        db.close()
