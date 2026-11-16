import os
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite:///analytics.db")


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Creates and returns a SQLAlchemy Engine for the target database."""
    url = db_url or os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    return create_engine(url)


def get_schema_metadata(engine: Optional[Engine] = None) -> str:
    """
    Inspects database tables and columns using SQLAlchemy reflection properties.
    Returns a structured textual representation of the schema.
    """
    eng = engine or get_engine()
    inspector = inspect(eng)
    table_names = inspector.get_table_names()

    if not table_names:
        return "Database has no tables."

    schema_lines = []
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []
        
        col_defs = []
        for col in columns:
            col_name = col["name"]
            col_type = str(col["type"])
            is_pk = " PRIMARY KEY" if col_name in pk_cols else ""
            nullable = "" if col.get("nullable", True) else " NOT NULL"
            col_defs.append(f"  {col_name} {col_type}{is_pk}{nullable}")

        schema_lines.append(f"Table: {table_name}")
        schema_lines.append("Columns:\n" + "\n".join(col_defs))
        schema_lines.append("")

    return "\n".join(schema_lines).strip()


def execute_sql_query(
    sql_query: str, engine: Optional[Engine] = None
) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Executes a SQL statement against the configured database.
    Returns:
        (success: bool, rows: List[Dict[str, Any]] | None, error_message: str | None)
    """
    eng = engine or get_engine()
    clean_query = sql_query.strip().rstrip(";")

    try:
        with eng.connect() as conn:
            result = conn.execute(text(clean_query))
            if result.returns_rows:
                rows = [dict(row._mapping) for row in result.fetchall()]
            else:
                conn.commit()
                rows = [{"affected_rows": result.rowcount}]
            return True, rows, None
    except SQLAlchemyError as exc:
        # Extract clean driver error message
        return False, None, str(exc)
    except Exception as exc:
        return False, None, str(exc)


def seed_database(engine: Optional[Engine] = None) -> None:
    """
    Seeds database with sample tables:
    - orders (id, order_date, customer_name, amount, status)
    - products (id, product_name, category, price, stock)
    """
    eng = engine or get_engine()

    with eng.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS orders;"))
        conn.execute(text("DROP TABLE IF EXISTS products;"))

        # Orders table as required by assessment brief
        conn.execute(
            text(
                """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                order_date TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL
            );
            """
            )
        )

        # Products table for richer analytics
        conn.execute(
            text(
                """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            );
            """
            )
        )

        # Sample Orders
        conn.execute(
            text(
                """
            INSERT INTO orders (id, order_date, customer_name, amount, status) VALUES
            (1, '2024-01-15', 'Alice Smith', 120.50, 'Completed'),
            (2, '2024-02-10', 'Bob Johnson', 250.00, 'Completed'),
            (3, '2024-02-18', 'Charlie Brown', 89.99, 'Pending'),
            (4, '2024-03-01', 'Diana Prince', 340.20, 'Completed'),
            (5, '2024-03-12', 'Evan Wright', 45.00, 'Cancelled'),
            (6, '2024-03-25', 'Fiona Gallagher', 510.75, 'Completed'),
            (7, '2024-04-02', 'George Clark', 190.00, 'Completed');
            """
            )
        )

        # Sample Products
        conn.execute(
            text(
                """
            INSERT INTO products (id, product_name, category, price, stock) VALUES
            (101, 'Wireless Keyboard', 'Electronics', 49.99, 120),
            (102, 'Optical Mouse', 'Electronics', 25.50, 200),
            (103, 'USB-C Monitor 27"', 'Electronics', 299.99, 45),
            (104, 'Ergonomic Desk Chair', 'Furniture', 189.00, 30),
            (105, 'Standing Desk Converter', 'Furniture', 149.50, 18),
            (106, 'Leather Notebook', 'Stationery', 14.99, 350);
            """
            )
        )
