import pytest

from app.db.session import check_db_connection


@pytest.mark.integration
def test_db_connection():
    assert check_db_connection() is True
