"""
QLNNN Offline - Import Data Module
Port từ Bigquerry_Connector.gs - Import Excel/CSV
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection
from utils.date_utils import format_date_for_db, parse_date_vn
from utils.text_utils import normalize_passport, normalize_header
from utils.validators import validate_import_row, ImportValidator
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
    Optimized for bulk insertion/update
    
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
    
    # Prepare data for bulk operation
    
    # 1. Normalize passport (Critical)
    initial_count = len(df)
    df['so_ho_chieu'] = df['so_ho_chieu'].astype(str).apply(normalize_passport)
    
    # Filter invalid passports
    df = df[df['so_ho_chieu'].astype(bool)]
    
    rows_skipped = initial_count - len(df)

    if df.empty:
        return {
            "success": True,
            "rows_imported": 0,
            "rows_skipped": rows_skipped,
            "source_file": source_name
        }

    # 2. Normalize other fields
    if 'ho_ten' in df.columns:
        df['ho_ten'] = df['ho_ten'].astype(str).str.strip().where(df['ho_ten'].notna(), None)
    else:
        df['ho_ten'] = None

    if 'quoc_tich' in df.columns:
        df['quoc_tich'] = df['quoc_tich'].astype(str).str.strip().str.upper().where(df['quoc_tich'].notna(), None)
    else:
        df['quoc_tich'] = None

    if 'dia_chi' in df.columns:
        df['dia_chi_tam_tru'] = df['dia_chi'].astype(str).str.strip().where(df['dia_chi'].notna(), None)
    elif 'dia_chi_tam_tru' not in df.columns:
        df['dia_chi_tam_tru'] = None

    if 'ket_qua_xac_minh' in df.columns:
        df['ket_qua_xac_minh'] = df['ket_qua_xac_minh'].astype(str).str.strip().where(df['ket_qua_xac_minh'].notna(), None)
    else:
        df['ket_qua_xac_minh'] = None

    # Date formatting
    def safe_format_date(val):
        if pd.isna(val) or str(val).lower() == 'nan':
            return None
        return format_date_for_db(str(val))

    for date_col in ['ngay_sinh', 'ngay_den', 'ngay_di']:
        if date_col in df.columns:
             df[date_col] = df[date_col].apply(safe_format_date)
        else:
            df[date_col] = None

    # ==========================================
    # VALIDATION
    # ==========================================
    valid_rows = []
    validation_report = {
        "total_errors": 0,
        "total_warnings": 0,
        "details": []
    }
    
    # We need to iterate to validate
    validator = ImportValidator()
    
    # Create a list of dicts for faster iteration
    records = df.to_dict('records')
    
    for idx, row in enumerate(records):
        # Reset validator for new row
        validator.reset()
        
        # Run validation
        validate_import_row(row, idx + 2, validator) # idx + 2 because 0-index + header
        
        result = validator.get_result()
        
        if result.is_valid:
            valid_rows.append(row)
        
        # Collect errors/warnings if any
        if result.error_count > 0 or result.warning_count > 0:
            validation_report["total_errors"] += result.error_count
            validation_report["total_warnings"] += result.warning_count
            
            if len(validation_report["details"]) < 100: # Limit report size
                validation_report["details"].append(result.to_dict())
    
    # Update stats
    rows_rejected = len(df) - len(valid_rows)
    
    if not valid_rows:
        return {
            "success": False,
            "error": f"All rows failed validation. See report.",
            "rows_imported": 0,
            "rows_skipped": rows_skipped + rows_rejected,
            "validation_report": validation_report
        }
    
    # Re-create DataFrame with only valid rows
    if valid_rows:
        df = pd.DataFrame(valid_rows)
    else:
        # Should be handled by check above, but for safety
        df = pd.DataFrame(columns=df.columns)
        
    # ==========================================

    # Add source file
    df['source_file'] = source_name

    # Select only necessary columns
    cols_to_keep = [
        'so_ho_chieu', 'ho_ten', 'ngay_sinh', 'quoc_tich', 'ngay_den',
        'ngay_di', 'dia_chi_tam_tru', 'ket_qua_xac_minh', 'source_file'
    ]

    # Ensure all columns exist
    for col in cols_to_keep:
        if col not in df.columns:
            df[col] = None

    final_df = df[cols_to_keep]

    try:
        # Register dataframe as a view
        conn.register('temp_import_data', final_df)

        # 1. Update existing records
        # Update logic: Match on passport AND arrival date (ngay_den)
        # Note: We use COALESCE for ket_qua_xac_minh to preserve existing verification if input is null
        conn.execute("""
            UPDATE raw_immigration
            SET
                ho_ten = t.ho_ten,
                ngay_sinh = t.ngay_sinh,
                quoc_tich = t.quoc_tich,
                ngay_di = t.ngay_di,
                dia_chi_tam_tru = t.dia_chi_tam_tru,
                ket_qua_xac_minh = CASE
                    WHEN t.ket_qua_xac_minh IS NOT NULL AND t.ket_qua_xac_minh != '' THEN t.ket_qua_xac_minh
                    ELSE raw_immigration.ket_qua_xac_minh
                END,
                source_file = t.source_file,
                thoi_diem_cap_nhat = CURRENT_TIMESTAMP
            FROM temp_import_data t
            WHERE raw_immigration.so_ho_chieu = t.so_ho_chieu
              AND raw_immigration.ngay_den = t.ngay_den
        """)

        # 2. Insert new records
        conn.execute("""
            INSERT INTO raw_immigration (
                so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den,
                ngay_di, dia_chi_tam_tru, ket_qua_xac_minh, source_file, thoi_diem_cap_nhat
            )
            SELECT
                t.so_ho_chieu, t.ho_ten, t.ngay_sinh, t.quoc_tich, t.ngay_den,
                t.ngay_di, t.dia_chi_tam_tru, t.ket_qua_xac_minh, t.source_file, CURRENT_TIMESTAMP
            FROM temp_import_data t
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_immigration r
                WHERE r.so_ho_chieu = t.so_ho_chieu
                  AND r.ngay_den = t.ngay_den
            )
        """)

        conn.commit()

        try:
            st.cache_data.clear()
        except Exception:
            pass

        return {
            "success": True,
            "rows_imported": len(final_df),
            "rows_skipped": rows_skipped + rows_rejected,
            "errors": None,
            "validation_report": validation_report,
            "source_file": source_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_imported": 0,
            "rows_skipped": initial_count
        }
    finally:
        # Always try to cleanup the view
        try:
            conn.unregister('temp_import_data')
        except Exception:
            pass


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
        
        try:
            st.cache_data.clear()
        except Exception:
            pass

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
        
        try:
            st.cache_data.clear()
        except Exception:
            pass

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
