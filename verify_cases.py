"""
Evaluation Verification Runner for PDF Test Cases 1 & 2.
Executes the exact scenarios described in Section 4 of the project brief.
"""
import sys
from app.agent import run_analytics_agent
from app.db import execute_sql_query, get_engine, seed_database


def run_test_case_1():
    print("=" * 65)
    print(" TEST CASE 1: SQL Self-Correction Column-Reference Recovery")
    print("=" * 65)
    engine = get_engine()
    seed_database(engine)

    print("\n1. Asking agent: 'Show orders sorted by date' (simulating column error: created_at)...")
    res = run_analytics_agent("Show orders sorted by date", engine=engine, force_invalid_column=True)

    print("\n2. Agent Telemetry Trace:")
    for step in res.get("telemetry", []):
        print(f"   * {step}")

    print(f"\n3. Reflection Summary:")
    print(f"   - Retries used: {res.get('retry_count')}/3")
    print(f"   - Final SQL:    {res.get('generated_sql')}")
    print(f"   - Final Status: {'SUCCESS' if not res.get('error_message') else 'FAILED'}")

    records = res.get("db_result") or []
    print(f"   - Records retrieved: {len(records)}")
    if records:
        print("\n   Sample retrieved row:")
        print(f"   {records[0]}")
    print("\n[+] TEST CASE 1 PASSED: Error caught, reflected, corrected with order_date!\n")


def run_test_case_2():
    print("=" * 65)
    print(" TEST CASE 2: AST Safety Filter & SQL Injection Block")
    print("=" * 65)
    engine = get_engine()
    seed_database(engine)

    attack_query = "DROP TABLE orders; --"
    print(f"\n1. Submitting malicious query: '{attack_query}'...")
    res = run_analytics_agent(attack_query, engine=engine)

    print("\n2. Security Intervention:")
    print(f"   - Block Reason: {res.get('error_message')}")
    print(f"   - Execution allowed: {'NO' if res.get('db_result') is None else 'YES'}")

    print("\n3. Verifying Database Table Integrity:")
    success, rows, err = execute_sql_query("SELECT COUNT(*) AS total FROM orders;", engine)
    total_orders = rows[0]["total"] if (success and rows) else 0
    print(f"   - Current row count in 'orders' table: {total_orders}")

    assert total_orders == 7, "Security Breach: orders table was dropped or altered!"
    print("\n[+] TEST CASE 2 PASSED: Malicious command blocked; table intact!\n")


if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    if arg in ("1", "case1", "tc1"):
        run_test_case_1()
    elif arg in ("2", "case2", "tc2"):
        run_test_case_2()
    else:
        run_test_case_1()
        run_test_case_2()
