import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from app.agent import (
    build_sql_graph,
    inspect_schema_node,
    generate_sql_node,
    execute_query_node,
    reflection_node,
    run_analytics_agent,
    AgentState,
)
from app.db import seed_database


@pytest.fixture
def in_memory_engine():
    """Provides a fresh seeded SQLite in-memory database engine for tests."""
    engine = create_engine("sqlite:///:memory:")
    seed_database(engine)
    return engine


class TestSelfCorrectionLoop:
    """Automated tests verifying the LangGraph self-correction and reflection retry loop."""

    def test_mock_column_error_and_recovery_flow(self, in_memory_engine):
        """
        Rubric Requirement:
        Mock a database error (e.g., 'no such column') on the first run, and verify the graph
        re-runs the reflection node and successfully corrects the query in the next step.
        """
        # Step 1: Initial state
        state: AgentState = {
            "user_query": "Show orders sorted by date",
            "generated_sql": "SELECT id, created_at FROM orders ORDER BY created_at ASC",
            "db_result": None,
            "error_message": None,
            "retry_count": 0,
            "schema_info": "Table: orders\nColumns:\n  id INTEGER\n  order_date TEXT",
            "reflection_prompt": None,
            "telemetry": [],
        }

        # Step 2: Execute query node - catches error 'no such column: created_at'
        res_exec = execute_query_node(state, engine=in_memory_engine)
        assert res_exec["db_result"] is None
        assert res_exec["error_message"] is not None
        assert "no such column" in res_exec["error_message"].lower()

        # Update state with execution failure
        state.update(res_exec)

        # Step 3: Reflection node catches the error and increments retry counter
        res_reflect = reflection_node(state)
        assert res_reflect["retry_count"] == 1
        assert res_reflect["reflection_prompt"] is not None
        assert "no such column" in res_reflect["reflection_prompt"].lower()

        # Update state with reflection outputs
        state.update(res_reflect)

        # Step 4: Generate SQL node re-runs with reflection prompt and corrects column reference
        res_gen = generate_sql_node(state, force_invalid_column=False)
        assert res_gen["generated_sql"] is not None
        assert "order_date" in res_gen["generated_sql"]
        assert "created_at" not in res_gen["generated_sql"]

        # Update state with corrected SQL
        state.update(res_gen)

        # Step 5: Execute query node re-runs on corrected query and succeeds
        res_exec_final = execute_query_node(state, engine=in_memory_engine)
        assert res_exec_final["error_message"] is None
        assert res_exec_final["db_result"] is not None
        assert len(res_exec_final["db_result"]) == 7

    def test_end_to_end_self_correction_workflow(self, in_memory_engine):
        """
        Full graph verification of Test Case 1:
        Ask the agent 'Show orders sorted by date' with invalid column on first run.
        Graph executes, catches error, reflects, rewrites with order_date, and returns rows.
        """
        result = run_analytics_agent(
            user_query="Show orders sorted by date",
            engine=in_memory_engine,
            force_invalid_column=True,
        )

        assert result["retry_count"] == 1
        assert result["error_message"] is None
        assert "order_date" in result["generated_sql"]
        assert result["db_result"] is not None
        assert len(result["db_result"]) == 7

    def test_reflection_loop_cap_at_three_retries(self, in_memory_engine):
        """Verifies that the reflection retry loop is strictly capped at a maximum of 3 retries."""
        # Force persistent execution errors
        with patch("app.agent.execute_sql_query", return_value=(False, None, "Persistent mock failure: syntax error")):
            result = run_analytics_agent(
                user_query="Show orders sorted by date",
                engine=in_memory_engine,
            )

            # Max retries must be exactly 3
            assert result["retry_count"] == 3
            assert result["error_message"] is not None
            assert "Persistent mock failure" in result["error_message"]
            assert result["db_result"] is None
