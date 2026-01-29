import sys
import os
from pathlib import Path
import duckdb
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_connection

def check_connection():
    try:
        conn = get_connection()
        print(f"Connection Object: {conn}")
        print(f"Type: {type(conn)}")

        if isinstance(conn, duckdb.DuckDBPyConnection):
            print("✅ Confirmed: Connection is DuckDBPyConnection")

            # Verify register method exists
            if hasattr(conn, 'register'):
                print("✅ Confirmed: register method exists")
            else:
                print("❌ Failed: register method MISSING")

        elif isinstance(conn, sqlite3.Connection):
             print("⚠️ Warning: Connection is sqlite3.Connection")
        else:
             print("❓ Unknown connection type")

    except Exception as e:
        print(f"❌ Error checking connection: {e}")

if __name__ == "__main__":
    check_connection()
