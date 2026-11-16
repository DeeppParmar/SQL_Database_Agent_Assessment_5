import pytest
from app.guardrails import is_safe_select_only, scan_user_input


class TestASTSafetyFilter:
    """Automated tests verifying AST SQL parser security boundaries."""

    def test_allow_valid_select_queries(self):
        valid_queries = [
            "SELECT * FROM orders;",
            "SELECT id, order_date, amount FROM orders WHERE amount > 100 ORDER BY order_date ASC",
            "SELECT category, COUNT(*) FROM products GROUP BY category HAVING COUNT(*) > 1",
            "WITH recent_orders AS (SELECT id, amount FROM orders) SELECT * FROM recent_orders",
        ]
        for query in valid_queries:
            assert is_safe_select_only(query) is True, f"Failed to allow valid query: {query}"

    def test_reject_write_queries(self):
        """Rubric Assertion: Assert the AST parser successfully catches and rejects write queries."""
        write_queries = [
            "DELETE FROM users",
            "DELETE FROM orders WHERE id = 1;",
            "DROP TABLE orders; --",
            "DROP TABLE IF EXISTS products;",
            "INSERT INTO orders (id, amount) VALUES (99, 10.5);",
            "UPDATE orders SET amount = 0;",
            "ALTER TABLE orders ADD COLUMN malicious_payload TEXT;",
            "TRUNCATE TABLE orders;",
        ]
        for query in write_queries:
            assert is_safe_select_only(query) is False, f"Failed to reject write query: {query}"

    def test_reject_multi_statement_injection(self):
        chained_attacks = [
            "SELECT * FROM orders; DROP TABLE orders;",
            "SELECT * FROM orders; DELETE FROM orders;",
            "SELECT 1; UPDATE users SET role='admin';",
        ]
        for attack in chained_attacks:
            assert is_safe_select_only(attack) is False, f"Failed to block chained attack: {attack}"

    def test_reject_empty_or_whitespace(self):
        assert is_safe_select_only("") is False
        assert is_safe_select_only("   ") is False


class TestNeMoInputGuardrails:
    """Automated tests verifying NeMo Guardrails input moderation layer."""

    def test_allow_benign_questions(self):
        safe_inputs = [
            "Show orders sorted by date",
            "What are the top 5 highest selling products?",
            "List all completed orders in February 2024",
            "How many items are currently in stock for electronics?",
        ]
        for user_text in safe_inputs:
            is_safe, error_msg = scan_user_input(user_text)
            assert is_safe is True, f"Benign input incorrectly blocked: {user_text} ({error_msg})"
            assert error_msg is None

    def test_block_sql_drop_table_injection(self):
        """Rubric Test Case 2: Verify NeMo Guardrails catches 'DROP TABLE orders; --'."""
        user_input = "DROP TABLE orders; --"
        is_safe, error_msg = scan_user_input(user_input)
        assert is_safe is False
        assert error_msg is not None
        assert "Destructive SQL command" in error_msg or "NeMo Guardrails" in error_msg

    def test_block_tautology_patterns(self):
        tautologies = [
            "Show orders WHERE 1=1",
            "SELECT * FROM users WHERE 'a'='a'",
            "Find users OR 1=1",
        ]
        for attack in tautologies:
            is_safe, error_msg = scan_user_input(attack)
            assert is_safe is False, f"Failed to block tautology: {attack}"
            assert "tautology" in error_msg.lower() or "security" in error_msg.lower()

    def test_block_comment_expansion_attacks(self):
        comment_attacks = [
            "orders; -- fetch admin password",
            "show products /* ignore where clause */",
        ]
        for attack in comment_attacks:
            is_safe, error_msg = scan_user_input(attack)
            assert is_safe is False, f"Failed to block comment expansion: {attack}"

    def test_block_script_tags_xss(self):
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<script src='evil.js'></script>",
            "javascript:void(0)",
        ]
        for attack in xss_inputs:
            is_safe, error_msg = scan_user_input(attack)
            assert is_safe is False, f"Failed to block XSS attack: {attack}"
            assert "script" in error_msg.lower() or "xss" in error_msg.lower()
