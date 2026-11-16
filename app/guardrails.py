import os
import re
from typing import Optional, Tuple
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import DDL, DML, Keyword

try:
    from nemoguardrails import RailsConfig, LLMRails
    from config.guardrails.actions import check_input_safety as nemo_action_check_safety
    _NEMO_AVAILABLE = True
except Exception:
    _NEMO_AVAILABLE = False


FORBIDDEN_KEYWORDS = {
    "DROP",
    "DELETE",
    "INSERT",
    "UPDATE",
    "ALTER",
    "TRUNCATE",
    "REPLACE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
}


def is_safe_select_only(sql_query: str) -> bool:
    """
    Abstract Syntax Tree (AST) analyzer using sqlparse.
    Validates that the generated SQL query is strictly read-only (SELECT / WITH CTE).
    Explicitly blocks write, modification, and administrative operations:
    INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.
    """
    if not sql_query or not sql_query.strip():
        return False

    clean_sql = sql_query.strip().rstrip(";")
    parsed = sqlparse.parse(clean_sql)

    if not parsed:
        return False

    for statement in parsed:
        # Check statement type
        stmt_type = statement.get_type()
        if stmt_type != "SELECT":
            return False

        # Deep AST token walk to ensure no nested forbidden write keywords
        for token in statement.flatten():
            token_val = token.value.strip().upper()
            if token_val in FORBIDDEN_KEYWORDS:
                return False

    return True


def scan_user_input(user_query: str) -> Tuple[bool, Optional[str]]:
    """
    Scans raw user input before sending to LLM.
    Blocks malicious input patterns such as tautologies, comment expansions,
    script tags, or direct destructive SQL injections.
    Uses NeMo Guardrails action scanner.
    """
    if not user_query or not user_query.strip():
        return False, "Empty query provided."

    if _NEMO_AVAILABLE:
        try:
            is_safe, reason = nemo_action_check_safety(user_input=user_query)
            if not is_safe:
                return False, f"Security Warning [NeMo Guardrails]: {reason}"
            return True, None
        except Exception:
            pass

    return _regex_fallback_scan(user_query)


def _regex_fallback_scan(user_query: str) -> Tuple[bool, Optional[str]]:
    """Internal robust regex safety validator for input sanitization."""
    text = user_query.strip()

    # Script tag check (XSS)
    if re.search(r"(<script\b[^>]*>|javascript:|onerror\s*=|onload\s*=)", text, re.IGNORECASE):
        return False, "Security Warning: Script tag / XSS payload detected."

    # Direct destructive SQL statements
    if re.search(
        r"\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|UPDATE\s+\w+\s+SET)\b",
        text,
        re.IGNORECASE,
    ):
        return False, "Security Warning: Destructive SQL command detected in input."

    # SQL comment expansions (e.g., 'DROP TABLE orders; --', '/* ... */')
    if re.search(r"(--|/\*|\*/|#\s*$)", text):
        return False, "Security Warning: Malicious SQL comment expansion detected."

    # Tautology patterns (e.g. '1=1', 'OR 1=1', 'OR 'a'='a'')
    if re.search(
        r"(\b(OR|AND|WHERE)\b\s+(['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?|1\s*=\s*1|'1'='1'|\bTRUE\b|\bFALSE\b)|1\s*=\s*1|'a'\s*=\s*'a')",
        text,
        re.IGNORECASE,
    ):
        return False, "Security Warning: SQL tautology injection pattern detected."

    return True, None
