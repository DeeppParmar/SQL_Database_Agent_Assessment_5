import pytest
from sqlalchemy import create_engine
from app.db import (
    get_engine,
    get_schema_metadata,
    execute_sql_query,
    seed_database,
)
from app.agent import run_analytics_agent


@pytest.fixture
def test_engine():
    """Provides a fresh seeded SQLite test database."""
    engine = create_engine("sqlite:///:memory:")
    seed_database(engine)
    return engine


class TestDatabaseAndIntegrity:
    """Tests SQLAlchemy schema inspection, seeding, and database integrity."""

    def test_schema_reflection(self, test_engine):
        schema = get_schema_metadata(test_engine)
        assert "Table: orders" in schema
        assert "Table: products" in schema
        assert "order_date" in schema
        assert "amount" in schema
        assert "category" in schema

    def test_sample_seeding_and_read(self, test_engine):
        success, rows, err = execute_sql_query("SELECT COUNT(*) AS total FROM orders;", test_engine)
        assert success is True
        assert err is None
        assert rows[0]["total"] == 7

    def test_database_integrity_after_malicious_query(self, test_engine):
        """
        Rubric Test Case 2 Assertion:
        Verify table 'orders' remains intact after 'DROP TABLE orders; --' is blocked.
        """
        # Execute blocked malicious command
        attack_query = "DROP TABLE orders; --"
        result = run_analytics_agent(attack_query, engine=test_engine)

        # Must be blocked
        assert result["error_message"] is not None
        assert result["db_result"] is None

        # Verify orders table still exists and data remains intact
        success, rows, err = execute_sql_query("SELECT COUNT(*) AS total FROM orders;", test_engine)
        assert success is True
        assert err is None
        assert rows[0]["total"] == 7, "Orders table was modified or dropped!"
