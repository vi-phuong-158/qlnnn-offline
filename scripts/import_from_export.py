"""
QLNNN - Import dữ liệu từ BigQuery export vào DuckDB
Chạy sau khi đã export từ BigQuery
"""

import pandas as pd
from pathlib import Path
import sys
import io

# Fix encoding for Windows console
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_connection
from database.models import init_database

# ============================================
# CẤU HÌNH
# ============================================

EXPORT_DIR = Path(__file__).parent.parent / "data" / "bigquery_export"


def read_csv_safe(file_path):
    """Read CSV with encoding fallback"""
    encodings = ["utf-8-sig", "utf-8", "cp1252", "utf-16"]
    
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # If it's not an encoding error, raise it
            raise e
            
    raise ValueError(f"Could not decode {file_path} with supported encodings")


def import_main_table(conn, csv_path):
    """Import raw_immigration table"""
    print(f"📥 Importing {csv_path.name}...")
    
    try:
        df = read_csv_safe(csv_path)
    except Exception as e:
        print(f"   ❌ Failed to read file: {e}")
        return

    print(f"   Found {len(df)} rows. Bulk inserting...")
    
    # Pre-process data
    if 'so_ho_chieu' in df.columns:
        df['so_ho_chieu'] = df['so_ho_chieu'].astype(str).str.strip().str.upper()
    
    # Add source column
    df['source_file'] = 'bigquery_export'
    
    # Ensure all columns exist
    required_cols = ["so_ho_chieu", "ho_ten", "ngay_sinh", "quoc_tich", "ngay_den", 
                     "ngay_di", "dia_chi_tam_tru", "ket_qua_xac_minh", "thoi_diem_cap_nhat"]
    
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
            
    try:
        # Register DataFrame as a virtual table
        conn.register('temp_main_import', df)
        
        # Bulk Insert
        conn.execute("""
            INSERT INTO raw_immigration 
            (so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den, ngay_di,
             dia_chi_tam_tru, ket_qua_xac_minh, thoi_diem_cap_nhat, source_file)
            SELECT 
                so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den, ngay_di,
                dia_chi_tam_tru, ket_qua_xac_minh, thoi_diem_cap_nhat, source_file
            FROM temp_main_import
        """)
        
        conn.unregister('temp_main_import')
        conn.commit()
        print(f"   ✅ Imported {len(df)} rows successfully!")
        
    except Exception as e:
        print(f"   ❌ Bulk insert failed: {e}")


def import_ref_table(conn, csv_path, table_name, columns):
    """Import a reference table"""
    print(f"📥 Importing {csv_path.name}...")
    
    if not csv_path.exists():
        print(f"   ⚠️ File not found, skipping")
        return
    
    try:
        df = read_csv_safe(csv_path)
    except Exception as e:
        print(f"   ❌ Failed to read file: {e}")
        return

    print(f"   Found {len(df)} rows. Bulk inserting...")
    
    # Pre-process
    for col in columns:
        if col not in df.columns:
            df[col] = None
        elif col == "so_ho_chieu":
            df[col] = df[col].astype(str).str.strip().str.upper()
        # Clean up strings
        elif df[col].dtype == object:
             df[col] = df[col].astype(str).str.strip()
             
    # Filter valid rows (has passport)
    if 'so_ho_chieu' in columns:
        df = df[df['so_ho_chieu'].notna() & (df['so_ho_chieu'] != '') & (df['so_ho_chieu'] != 'NAN')]
    
    if df.empty:
        print("   ⚠️ No valid data found")
        return

    try:
        # Register DataFrame
        table_alias = f"temp_{table_name}_import"
        conn.register(table_alias, df)
        
        # Build SQL
        col_list = ", ".join(columns)
        
        # Use INSERT OR REPLACE/IGNORE if needed, but standard INSERT is fast
        # Using INSERT OR IGNORE to skip duplicates
        conn.execute(f"""
            INSERT OR IGNORE INTO {table_name} ({col_list})
            SELECT {col_list} FROM {table_alias}
        """)
        
        conn.unregister(table_alias)
        conn.commit()
        print(f"   ✅ Imported {len(df)} rows successfully!")
        
    except Exception as e:
        print(f"   ❌ Bulk insert failed: {e}")


def main():
    print("=" * 50)
    print("QLNNN - Import BigQuery Export to DuckDB")
    print("=" * 50)
    
    if not EXPORT_DIR.exists():
        print(f"❌ Export directory not found: {EXPORT_DIR}")
        print("\nHướng dẫn:")
        print("1. Chạy export_bigquery.py trước")
        print("2. Copy thư mục 'bigquery_export' vào 'qlnnn_offline/data/'")
        return
    

    # Initialize database
    print("\n🔧 Initializing database...")
    
    # Clean up old database to ensure new schema (with sequences) is applied
    from config import DATABASE_PATH
    if DATABASE_PATH.exists():
        try:
            # Close any existing connections first (just in case)
            import database.connection
            database.connection.close_connection()
            DATABASE_PATH.unlink()
            print(f"🗑️ Deleted old database: {DATABASE_PATH}")
        except Exception as e:
            print(f"⚠️ Could not delete database: {e}")
            
    init_database()
    
    conn = get_connection()
    
    # Import main table
    main_csv = EXPORT_DIR / "raw_immigration.csv"
    if main_csv.exists():
        import_main_table(conn, main_csv)
    else:
        print(f"⚠️ Main table not found: {main_csv}")
    
    # Import reference tables
    ref_tables = {
        "ref_labor": ["so_ho_chieu", "vi_tri", "noi_lam_viec", "ngay_cap"],
        "ref_student": ["so_ho_chieu", "truong", "nganh"],
        "ref_watchlist": ["so_ho_chieu", "dien", "so_cong_van", "ngay_nhap"],
        "ref_marriage": ["so_ho_chieu", "ho_ten_vn", "dia_chi", "dien"]
    }
    
    for table, columns in ref_tables.items():
        csv_path = EXPORT_DIR / f"{table}.csv"
        import_ref_table(conn, csv_path, table, columns)
    
    # Verify
    print("\n📊 Verification:")
    tables = ["raw_immigration", "ref_labor", "ref_student", "ref_watchlist", "ref_marriage"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   {table}: {count:,} rows")
    
    print("\n✅ Import hoàn tất!")
    print("Chạy 'streamlit run app.py' để khởi động ứng dụng")


if __name__ == "__main__":
    main()
