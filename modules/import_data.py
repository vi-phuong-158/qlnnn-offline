"""
QLNNN Offline - Import Data Module
Port từ Bigquerry_Connector.gs - Import Excel/CSV
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection
from utils.date_utils import format_date_for_db, parse_date_vn
from utils.text_utils import normalize_passport, normalize_header
from config import HEADER_MAP, IMPORTS_DIR


def import_excel(file_path: str, sheet_name: str = None) -> Dict[str, Any]:
    """
    Import data from Excel file
    
    Args:
        file_path: Path to Excel file
        sheet_name: Sheet name (optional, uses first sheet if not specified)
        
    Returns:
        Dict with import results
    """
    try:
        # Read Excel file
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        
        return _process_dataframe(df, file_path)
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_imported": 0,
            "rows_skipped": 0
        }


def import_csv(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Import data from CSV file
    
    Args:
        file_path: Path to CSV file
        encoding: File encoding (default: utf-8)
        
    Returns:
        Dict with import results
    """
    try:
        # Try common encodings if utf-8 fails
        encodings = [encoding, "utf-8-sig", "cp1252", "latin1"]
        
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            return {
                "success": False,
                "error": "Could not decode file with any supported encoding",
                "rows_imported": 0,
                "rows_skipped": 0
            }
        
        return _process_dataframe(df, file_path)
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_imported": 0,
            "rows_skipped": 0
        }


def _process_dataframe(df: pd.DataFrame, source_file: str) -> Dict[str, Any]:
    """
    Process a pandas DataFrame and insert into database
    
    Args:
        df: Pandas DataFrame
        source_file: Source file name for tracking
        
    Returns:
        Dict with import results
    """
    if df.empty:
        return {
            "success": False,
            "error": "File is empty",
            "rows_imported": 0,
            "rows_skipped": 0
        }
    
    # Normalize column names
    column_mapping = {}
    for col in df.columns:
        normalized = normalize_header(str(col))
        if normalized in HEADER_MAP:
            column_mapping[col] = HEADER_MAP[normalized]
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Check required columns
    required = ["so_ho_chieu"]
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        return {
            "success": False,
            "error": f"Missing required columns: {', '.join(missing)}",
            "rows_imported": 0,
            "rows_skipped": 0
        }
    
    conn = get_connection()
    source_name = Path(source_file).name
    
    rows_imported = 0
    rows_skipped = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Get passport (required)
            passport = normalize_passport(str(row.get("so_ho_chieu", "")))
            if not passport:
                rows_skipped += 1
                continue
            
            # Get other fields
            ho_ten = str(row.get("ho_ten", "")).strip() if pd.notna(row.get("ho_ten")) else None
            
            # Parse dates
            ngay_sinh = None
            if pd.notna(row.get("ngay_sinh")):
                ngay_sinh = format_date_for_db(str(row.get("ngay_sinh")))
            
            ngay_den = None
            if pd.notna(row.get("ngay_den")):
                ngay_den = format_date_for_db(str(row.get("ngay_den")))
            
            ngay_di = None
            if pd.notna(row.get("ngay_di")):
                ngay_di = format_date_for_db(str(row.get("ngay_di")))
            
            quoc_tich = str(row.get("quoc_tich", "")).strip().upper() if pd.notna(row.get("quoc_tich")) else None
            dia_chi = str(row.get("dia_chi", "")).strip() if pd.notna(row.get("dia_chi")) else None
            ket_qua = str(row.get("ket_qua_xac_minh", "")).strip() if pd.notna(row.get("ket_qua_xac_minh")) else None
            
            # Check for duplicates (Passport + Arrival Date)
            existing = conn.execute(
                "SELECT 1 FROM raw_immigration WHERE so_ho_chieu = ? AND ngay_den = ?", 
                (passport, ngay_den)
            ).fetchone()
            
            if existing:
                # Update existing record
                conn.execute("""
                    UPDATE raw_immigration 
                    SET ho_ten = ?, 
                        ngay_sinh = ?, 
                        quoc_tich = ?, 
                        ngay_di = ?, 
                        dia_chi_tam_tru = ?, 
                        ket_qua_xac_minh = COALESCE(?, ket_qua_xac_minh),
                        source_file = ?,
                        thoi_diem_cap_nhat = CURRENT_TIMESTAMP
                    WHERE so_ho_chieu = ? AND ngay_den = ?
                """, (
                    ho_ten, ngay_sinh, quoc_tich, ngay_di, dia_chi, ket_qua, source_name,
                    passport, ngay_den
                ))
            else:    
                # Insert into database
                conn.execute("""
                    INSERT INTO raw_immigration 
                    (so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den, ngay_di, 
                     dia_chi_tam_tru, ket_qua_xac_minh, source_file, thoi_diem_cap_nhat)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    passport, ho_ten, ngay_sinh, quoc_tich,
                    ngay_den, ngay_di, dia_chi, ket_qua, source_name
                ))
            
            rows_imported += 1
            
        except Exception as e:
            rows_skipped += 1
            if len(errors) < 5:
                errors.append(f"Row {idx + 2}: {str(e)}")
    
    conn.commit()
    
    return {
        "success": True,
        "rows_imported": rows_imported,
        "rows_skipped": rows_skipped,
        "errors": errors if errors else None,
        "source_file": source_name
    }


def import_verification_results(file_path: str) -> Dict[str, Any]:
    """
    Import verification results from CAX (Công an xã)
    Updates ket_qua_xac_minh field for existing records
    
    Args:
        file_path: Path to Excel/CSV file with verification results
        
    Returns:
        Dict with update results
    """
    try:
        # Detect file type
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Normalize columns
        column_mapping = {}
        for col in df.columns:
            normalized = normalize_header(str(col))
            if normalized in HEADER_MAP:
                column_mapping[col] = HEADER_MAP[normalized]
        
        df = df.rename(columns=column_mapping)
        
        # Required columns
        if "so_ho_chieu" not in df.columns or "ket_qua_xac_minh" not in df.columns:
            return {
                "success": False,
                "error": "File phải có cột 'so_ho_chieu' và 'ket_qua_xac_minh'",
                "rows_updated": 0
            }
        
        conn = get_connection()
        rows_updated = 0
        
        for _, row in df.iterrows():
            passport = normalize_passport(str(row.get("so_ho_chieu", "")))
            ket_qua = str(row.get("ket_qua_xac_minh", "")).strip()
            
            if not passport or not ket_qua:
                continue
            
            # Update matching records
            result = conn.execute("""
                UPDATE raw_immigration 
                SET ket_qua_xac_minh = ?, thoi_diem_cap_nhat = CURRENT_TIMESTAMP
                WHERE UPPER(so_ho_chieu) = ?
            """, (ket_qua, passport))
            
            rows_updated += 1
        
        conn.commit()
        
        return {
            "success": True,
            "rows_updated": rows_updated
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_updated": 0
        }


def import_reference_table(
    file_path: str, 
    table_name: str,
    required_columns: List[str]
) -> Dict[str, Any]:
    """
    Import data into a reference table (ref_labor, ref_watchlist, etc.)
    
    Args:
        file_path: Path to data file
        table_name: Target table name
        required_columns: List of required columns
        
    Returns:
        Import results
    """
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Normalize columns
        column_mapping = {}
        for col in df.columns:
            normalized = normalize_header(str(col))
            column_mapping[col] = normalized
        
        df = df.rename(columns=column_mapping)
        
        # Check required columns
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            return {
                "success": False,
                "error": f"Missing columns: {', '.join(missing)}",
                "rows_imported": 0
            }
        
        conn = get_connection()
        
        # Build insert SQL
        columns = [c for c in df.columns if c in required_columns or c == "so_ho_chieu"]
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        
        rows_imported = 0
        
        for _, row in df.iterrows():
            values = []
            for col in columns:
                val = row.get(col)
                if pd.isna(val):
                    values.append(None)
                elif col == "so_ho_chieu":
                    values.append(normalize_passport(str(val)))
                else:
                    values.append(str(val).strip())
            
            if not values[0]:  # Skip if no passport
                continue
            
            try:
                conn.execute(f"""
                    INSERT OR REPLACE INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                """, tuple(values))
                rows_imported += 1
            except Exception:
                continue
        
        conn.commit()
        
        return {
            "success": True,
            "rows_imported": rows_imported,
            "table": table_name
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_imported": 0
        }
