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


# Whitelist of allowed table names for safe queries
SAFE_TABLES = frozenset({
    'raw_immigration', 'ref_labor', 'ref_watchlist', 
    'ref_marriage', 'ref_student', 'users', 'audit_log'
})


def get_table_count(table_name: str) -> int:
    """
    Get row count of a whitelist-approved table.
    
    Args:
        table_name: Name of the table (must be in SAFE_TABLES)
        
    Returns:
        Number of rows
        
    Raises:
        ValueError: If table_name not in whitelist
    """
    if table_name not in SAFE_TABLES:
        raise ValueError(f"Table '{table_name}' not allowed")
    
    conn = get_connection()
    # Use identifier quoting for additional safety
    result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
    return result[0]


def create_performance_indexes() -> Dict[str, bool]:
    """
    Tạo các index tối ưu performance cho bảng raw_immigration.
    Index giúp tăng tốc:
    - Lọc trùng khi import (so_ho_chieu + ngay_den)
    - Thống kê theo quốc tịch
    
    Returns:
        Dict với tên index và trạng thái (True = tạo thành công)
    """
    conn = get_connection()
    results = {}
    
    indexes = [
        # Composite index cho lọc trùng - equality columns first
        ("idx_passport_ngayden", 
         "CREATE INDEX IF NOT EXISTS idx_passport_ngayden ON raw_immigration(so_ho_chieu, ngay_den)"),
        
        # Index cho thống kê theo quốc tịch
        ("idx_quoctich", 
         "CREATE INDEX IF NOT EXISTS idx_quoctich ON raw_immigration(quoc_tich)"),
    ]
    
    for index_name, sql in indexes:
        try:
            conn.execute(sql)
            results[index_name] = True
        except Exception as e:
            results[index_name] = False
            print(f"Warning: Could not create index {index_name}: {e}")
    
    conn.commit()
    return results


def get_indexes(table_name: str = "raw_immigration") -> List[Dict[str, Any]]:
    """
    Liệt kê các index của một bảng.
    
    Args:
        table_name: Tên bảng
        
    Returns:
        List các index với thông tin chi tiết
    """
    conn = get_connection()
    try:
        result = conn.execute(f"""
            SELECT index_name, is_unique, sql 
            FROM duckdb_indexes() 
            WHERE table_name = '{table_name}'
        """).fetchall()
        
        return [
            {"name": row[0], "unique": row[1], "sql": row[2]}
            for row in result
        ]
    except Exception:
        # Fallback for older DuckDB versions
        return []

