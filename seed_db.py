"""
Database Seeding Script
Populates the target database (SQLite or PostgreSQL) with orders and products tables.
"""
from app.db import get_engine, seed_database, get_schema_metadata

if __name__ == "__main__":
    engine = get_engine()
    print(f"Connecting to database at: {engine.url}")
    print("Seeding database tables...")
    seed_database(engine)
    print("Database seeded successfully!\n")
    print("Reflected Schema:")
    print(get_schema_metadata(engine))
