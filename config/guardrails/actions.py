import re
from typing import Optional, Tuple
from nemoguardrails.actions import action

# Malicious patterns to block:
# - Tautologies: 'or 1=1', 'where 1=1', 'or 'a'='a'', '1=1'
# - Comment expansions: '--', '/*', '*/'
# - Script tags: '<script>', 'javascript:'
# - Dangerous SQL DDL/DML statements directly injected in prompt
TAUTOLOGY_PATTERN = re.compile(
    r"(\b(OR|AND|WHERE)\b\s+(['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?|1\s*=\s*1|'1'='1'|\bTRUE\b|\bFALSE\b)|1\s*=\s*1|'a'\s*=\s*'a')",
    re.IGNORECASE,
)
COMMENT_PATTERN = re.compile(r"(--|/\*|\*/|#\s*$)", re.IGNORECASE)
SCRIPT_TAG_PATTERN = re.compile(r"(<script\b[^>]*>|javascript:|onerror\s*=|onload\s*=)", re.IGNORECASE)
DESTRUCTIVE_SQL_PATTERN = re.compile(
    r"\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|UPDATE\s+\w+\s+SET)\b",
    re.IGNORECASE,
)


@action(name="check_input_safety")
def check_input_safety(user_input: str = "") -> Tuple[bool, Optional[str]]:
    """Scans raw user input for malicious injection patterns."""
    text = user_input.strip()

    if SCRIPT_TAG_PATTERN.search(text):
        return False, "Cross-site scripting (XSS) / script tag injection detected"

    if DESTRUCTIVE_SQL_PATTERN.search(text):
        return False, "Destructive SQL statement injection detected"

    if TAUTOLOGY_PATTERN.search(text):
        return False, "SQL injection tautology pattern (e.g. 1=1, 'a'='a') detected"

    if COMMENT_PATTERN.search(text):
        return False, "SQL comment expansion attack ('--', '/*') detected"

    return True, None
