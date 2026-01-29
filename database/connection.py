"""
QLNNN Offline - Database Connection
DuckDB connection management
"""

import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH


# Global connection (singleton pattern for Streamlit)
_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Get or create database connection (singleton)
    
    Args:
        read_only: If True, open in read-only mode
        
    Returns:
        DuckDB connection object
    """
    global _connection
    
    if _connection is None:
        # Ensure data directory exists
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        _connection = duckdb.connect(
            str(DATABASE_PATH),
            read_only=read_only
        )
        
        
        # Enable case-insensitive LIKE by default
        # _connection.execute("PRAGMA case_insensitive_like=true")
    
    return _connection


def close_connection():
    """Close the database connection"""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


@contextmanager
def get_cursor():
    """
    Context manager for database cursor
    
    Usage:
        with get_cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def execute_query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dicts
    
    Args:
        sql: SQL query string
        params: Query parameters (optional)
        
    Returns:
        List of dictionaries with column names as keys
    """
    conn = get_connection()
    
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    
    # Get column names
    columns = [desc[0] for desc in result.description]
    
    # Fetch all rows and convert to dicts
    rows = result.fetchall()
    
    return [dict(zip(columns, row)) for row in rows]


def execute_many(sql: str, params_list: List[tuple]) -> int:
    """
    Execute a query with multiple parameter sets (bulk insert/update)
    
    Args:
        sql: SQL query string with placeholders
        params_list: List of parameter tuples
        
    Returns:
        Number of rows affected
    """
    conn = get_connection()
    
    total = 0
    for params in params_list:
        conn.execute(sql, params)
        total += 1
    
    conn.commit()
    return total


def execute_script(sql_script: str) -> None:
    """
    Execute a multi-statement SQL script
    
    Args:
        sql_script: SQL script with multiple statements
    """
    conn = get_connection()
    
    # Split by semicolon and execute each statement
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]
    
    for statement in statements:
        conn.execute(statement)
    
    conn.commit()


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database
    
    Args:
        table_name: Name of the table
        
    Returns:
        True if table exists
    """
    conn = get_connection()
    result = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        (table_name,)
    ).fetchone()
    
    return result[0] > 0


def get_table_count(table_name: str) -> int:
    """
    Get row count of a table
    
    Args:
        table_name: Name of the table
        
    Returns:
        Number of rows
    """
    conn = get_connection()
    result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return result[0]
