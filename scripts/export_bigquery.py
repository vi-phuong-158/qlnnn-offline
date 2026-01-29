"""
QLNNN - Script Export dữ liệu từ BigQuery
Chạy script này trên Google Colab hoặc môi trường có google-cloud-bigquery

HƯỚNG DẪN SỬ DỤNG:
1. Upload file này lên Google Colab
2. Upload file service account JSON
3. Chạy từng cell

Hoặc chạy trên máy local:
pip install google-cloud-bigquery pandas pyarrow
"""

from google.cloud import bigquery
import pandas as pd
from pathlib import Path

# ============================================
# CẤU HÌNH
# ============================================

# Thay đổi path đến file service account của bạn
SERVICE_ACCOUNT_FILE = "service_account.json"  

# BigQuery config
PROJECT_ID = "resolute-future-478306-e7"
DATASET_ID = "qlnnn_warehouse"

# Tables to export
TABLES = [
    "raw_immigration",
    "ref_labor",
    "ref_student",
    "ref_watchlist",
    "ref_marriage"
]

# Output directory
OUTPUT_DIR = Path("bigquery_export")
OUTPUT_DIR.mkdir(exist_ok=True)


def export_table(client, table_name):
    """Export a single table to CSV"""
    print(f"📥 Exporting {table_name}...")
    
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`"
    
    try:
        df = client.query(query).to_dataframe()
        
        # Save to CSV
        output_file = OUTPUT_DIR / f"{table_name}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        
        print(f"   ✅ Exported {len(df)} rows to {output_file}")
        return len(df)
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0


def main():
    """Main export function"""
    print("=" * 50)
    print("QLNNN - BigQuery Export Tool")
    print("=" * 50)
    
    # Initialize client
    try:
        client = bigquery.Client.from_service_account_json(SERVICE_ACCOUNT_FILE)
        print(f"✅ Connected to project: {client.project}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nHướng dẫn:")
        print("1. Tải service account JSON từ Google Cloud Console")
        print("2. Đặt file vào cùng thư mục với script này")
        print("3. Đổi tên thành 'service_account.json'")
        return
    
    print(f"\n📂 Output directory: {OUTPUT_DIR.absolute()}")
    print()
    
    # Export each table
    total_rows = 0
    for table in TABLES:
        rows = export_table(client, table)
        total_rows += rows
    
    print()
    print("=" * 50)
    print(f"✅ Export hoàn tất! Tổng cộng: {total_rows:,} rows")
    print(f"📂 Files exported to: {OUTPUT_DIR.absolute()}")
    print()
    print("Bước tiếp theo:")
    print("1. Copy thư mục 'bigquery_export' vào 'qlnnn_offline/data/'")
    print("2. Chạy 'python import_from_export.py' để import vào DuckDB")


if __name__ == "__main__":
    main()
