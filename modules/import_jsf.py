"""
QLNNN Offline - Import JSF Module
Xử lý import dữ liệu tạm trú từ file JSF (PDF)
Tích hợp với logic lọc trùng và validation hiện có
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection
from utils.date_utils import format_date_for_db
from utils.text_utils import normalize_passport, normalize_header
from utils.validators import validate_import_row, ImportValidator
from config import HEADER_MAP


# =============================================
# HEADER MAPPING CHO FILE JSF
# =============================================

JSF_HEADER_MAP = {
    # Mapping từ header tiếng Việt trong JSF sang tên cột chuẩn
    "stt": "stt",
    "họ tên": "ho_ten",
    "họ và tên": "ho_ten",
    "ngày sinh": "ngay_sinh",
    "gt": "gioi_tinh",
    "giới tính": "gioi_tinh",
    "qt": "quoc_tich",
    "quốc tịch": "quoc_tich",
    "số hộ chiếu": "so_ho_chieu",
    "ngày đến": "ngay_den",
    "ngày đi": "ngay_di",
    "số phòng": "so_phong",
    "địa chỉ tạm trú": "dia_chi_tam_tru",
    "địa chỉ": "dia_chi_tam_tru",
}

# Chunk size cho import file lớn (số dòng mỗi chunk)
CHUNK_SIZE = 5000


def extract_jsf_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Trích xuất dữ liệu từ file JSF (PDF) thành DataFrame.
    
    Args:
        file_path: Đường dẫn file JSF
        
    Returns:
        DataFrame hoặc None nếu lỗi
    """
    all_dfs = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return None
            
            for i, page in enumerate(pdf.pages, 1):
                table = page.extract_table()
                if table:
                    # Trang đầu có header
                    if i == 1:
                        df = pd.DataFrame(table[1:], columns=table[0])
                    else:
                        # Các trang sau, kiểm tra xem row đầu có phải header không
                        first_row = table[0]
                        if first_row and str(first_row[0]).upper() == 'STT':
                            # Bỏ qua header trùng
                            df = pd.DataFrame(table[1:], columns=table[0])
                        else:
                            # Không có header, dùng header từ trang 1
                            df = pd.DataFrame(table, columns=all_dfs[0].columns if all_dfs else None)
                    
                    all_dfs.append(df)
                    
    except Exception as e:
        print(f"Error reading JSF: {e}")
        return None

    if not all_dfs:
        return None

    # Ghép tất cả bảng
    df_all = pd.concat(all_dfs, ignore_index=True)
    
    # Làm sạch cột STT - loại bỏ dòng không phải số
    if 'STT' in df_all.columns:
        df_all = df_all[pd.to_numeric(df_all['STT'], errors='coerce').notna()]
    
    return df_all


def normalize_jsf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa tên cột từ JSF sang tên cột chuẩn.
    
    Args:
        df: DataFrame với cột gốc từ JSF
        
    Returns:
        DataFrame với cột đã chuẩn hóa
    """
    column_mapping = {}
    
    for col in df.columns:
        # Chuẩn hóa header: lowercase, strip
        normalized = str(col).lower().strip()
        
        # Tìm trong JSF_HEADER_MAP trước
        if normalized in JSF_HEADER_MAP:
            column_mapping[col] = JSF_HEADER_MAP[normalized]
        # Sau đó tìm trong HEADER_MAP chung
        elif normalized in HEADER_MAP:
            column_mapping[col] = HEADER_MAP[normalized]
    
    return df.rename(columns=column_mapping)


def normalize_jsf_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa các cột ngày tháng về format YYYY-MM-DD cho database.
    
    Args:
        df: DataFrame
        
    Returns:
        DataFrame với ngày đã chuẩn hóa
    """
    date_columns = ['ngay_sinh', 'ngay_den', 'ngay_di']
    
    for col in date_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: format_date_for_db(str(x)) if pd.notna(x) and str(x).strip() else None)
    
    return df


def import_jsf(file_path: str) -> Dict[str, Any]:
    """
    Import dữ liệu từ file JSF vào database.
    Bao gồm lọc trùng và validation.
    
    Args:
        file_path: Đường dẫn file JSF
        
    Returns:
        Dict với kết quả import
    """
    # 1. Trích xuất dữ liệu từ JSF
    df = extract_jsf_data(file_path)
    
    if df is None or df.empty:
        return {
            "success": False,
            "error": "Không thể đọc dữ liệu từ file JSF hoặc file trống",
            "rows_imported": 0,
            "rows_skipped": 0
        }
    
    initial_count = len(df)
    
    # 2. Chuẩn hóa tên cột
    df = normalize_jsf_columns(df)
    
    # 3. Kiểm tra cột bắt buộc
    if 'so_ho_chieu' not in df.columns:
        return {
            "success": False,
            "error": "Không tìm thấy cột 'Số hộ chiếu' trong file JSF",
            "rows_imported": 0,
            "rows_skipped": 0
        }
    
    # 4. Chuẩn hóa passport
    df['so_ho_chieu'] = df['so_ho_chieu'].astype(str).apply(normalize_passport)
    
    # Loại bỏ dòng không có passport hợp lệ
    df = df[df['so_ho_chieu'].astype(bool)]
    rows_invalid_passport = initial_count - len(df)
    
    if df.empty:
        return {
            "success": False,
            "error": "Tất cả các dòng đều có số hộ chiếu không hợp lệ",
            "rows_imported": 0,
            "rows_skipped": initial_count
        }
    
    # 5. Chuẩn hóa các trường khác
    if 'ho_ten' in df.columns:
        df['ho_ten'] = df['ho_ten'].astype(str).str.strip().replace('nan', None)
    else:
        df['ho_ten'] = None
    
    if 'quoc_tich' in df.columns:
        df['quoc_tich'] = df['quoc_tich'].astype(str).str.strip().str.upper().replace('NAN', None)
    else:
        df['quoc_tich'] = None
    
    if 'dia_chi_tam_tru' in df.columns:
        # Xử lý newline trong địa chỉ
        df['dia_chi_tam_tru'] = df['dia_chi_tam_tru'].astype(str).str.replace(r'\n', ', ', regex=True).str.strip().replace('nan', None)
    else:
        df['dia_chi_tam_tru'] = None
    
    # 6. Chuẩn hóa ngày tháng
    df = normalize_jsf_dates(df)
    
    # 7. Validation
    valid_rows = []
    validation_report = {
        "total_errors": 0,
        "total_warnings": 0,
        "details": []
    }
    
    validator = ImportValidator()
    records = df.to_dict('records')
    
    for idx, row in enumerate(records):
        validator.reset()
        validate_import_row(row, idx + 2, validator)
        result = validator.get_result()
        
        if result.is_valid:
            valid_rows.append(row)
        
        if result.error_count > 0 or result.warning_count > 0:
            validation_report["total_errors"] += result.error_count
            validation_report["total_warnings"] += result.warning_count
            
            if len(validation_report["details"]) < 50:
                validation_report["details"].append(result.to_dict())
    
    rows_validation_failed = len(df) - len(valid_rows)
    
    if not valid_rows:
        return {
            "success": False,
            "error": "Tất cả các dòng đều không qua được validation",
            "rows_imported": 0,
            "rows_skipped": initial_count,
            "validation_report": validation_report
        }
    
    # Tạo DataFrame từ valid rows
    df = pd.DataFrame(valid_rows)
    
    # 8. Thêm source file
    source_name = Path(file_path).name
    df['source_file'] = source_name
    
    # 9. Chuẩn bị cột cho database
    cols_to_keep = [
        'so_ho_chieu', 'ho_ten', 'ngay_sinh', 'quoc_tich', 'ngay_den',
        'ngay_di', 'dia_chi_tam_tru', 'source_file'
    ]
    
    # Thêm cột ket_qua_xac_minh nếu chưa có
    if 'ket_qua_xac_minh' not in df.columns:
        df['ket_qua_xac_minh'] = None
    cols_to_keep.append('ket_qua_xac_minh')
    
    # Đảm bảo tất cả cột tồn tại
    for col in cols_to_keep:
        if col not in df.columns:
            df[col] = None
    
    final_df = df[cols_to_keep]
    
    # 10. Insert/Update vào database với logic lọc trùng
    try:
        conn = get_connection()
        
        # Register dataframe as view
        conn.register('temp_jsf_import', final_df)
        
        # Update existing records (match on passport + ngay_den)
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
            FROM temp_jsf_import t
            WHERE raw_immigration.so_ho_chieu = t.so_ho_chieu
              AND raw_immigration.ngay_den = t.ngay_den
        """)
        
        # Get count of updated rows
        updated_result = conn.execute("""
            SELECT COUNT(*) as cnt FROM raw_immigration r
            WHERE EXISTS (
                SELECT 1 FROM temp_jsf_import t
                WHERE r.so_ho_chieu = t.so_ho_chieu
                  AND r.ngay_den = t.ngay_den
            )
        """).fetchone()
        rows_updated = updated_result[0] if updated_result else 0
        
        # Insert new records
        conn.execute("""
            INSERT INTO raw_immigration (
                so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den,
                ngay_di, dia_chi_tam_tru, ket_qua_xac_minh, source_file, thoi_diem_cap_nhat
            )
            SELECT
                t.so_ho_chieu, t.ho_ten, t.ngay_sinh, t.quoc_tich, t.ngay_den,
                t.ngay_di, t.dia_chi_tam_tru, t.ket_qua_xac_minh, t.source_file, CURRENT_TIMESTAMP
            FROM temp_jsf_import t
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_immigration r
                WHERE r.so_ho_chieu = t.so_ho_chieu
                  AND r.ngay_den = t.ngay_den
            )
        """)
        
        rows_inserted = len(final_df) - rows_updated
        
        conn.commit()
        
        try:
            st.cache_data.clear()
        except Exception:
            pass

        return {
            "success": True,
            "rows_imported": len(final_df),
            "rows_inserted": rows_inserted,
            "rows_updated": rows_updated,
            "rows_skipped": rows_invalid_passport + rows_validation_failed,
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
        try:
            conn.unregister('temp_jsf_import')
        except Exception:
            pass


def import_jsf_to_excel(file_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Import JSF và xuất ra Excel (không import vào database).
    Dùng để preview hoặc kiểm tra dữ liệu.
    
    Args:
        file_path: Đường dẫn file JSF
        output_path: Đường dẫn file Excel output (tùy chọn)
        
    Returns:
        Dict với thông tin kết quả
    """
    # Trích xuất dữ liệu
    df = extract_jsf_data(file_path)
    
    if df is None or df.empty:
        return {
            "success": False,
            "error": "Không thể đọc dữ liệu từ file JSF",
            "rows": 0
        }
    
    # Chuẩn hóa cột
    df = normalize_jsf_columns(df)
    
    # Chuẩn hóa ngày (giữ format DD/MM/YYYY cho Excel)
    date_columns = ['ngay_sinh', 'ngay_den', 'ngay_di']
    for col in date_columns:
        if col in df.columns:
            datetime_col = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            df[col] = datetime_col.apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')
    
    # Xác định output path
    if not output_path:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.dirname(file_path)
        output_path = os.path.join(output_dir, f"{base_name}_extracted.xlsx")
    
    # Lưu Excel
    df.to_excel(output_path, index=False)
    
    return {
        "success": True,
        "rows": len(df),
        "output_path": output_path,
        "columns": list(df.columns)
    }


def _process_and_import_chunk(
    chunk_df: pd.DataFrame, 
    source_name: str, 
    conn
) -> Dict[str, Any]:
    """
    Xử lý và import một chunk DataFrame vào database.
    Hàm nội bộ, được gọi bởi import_jsf_chunked().
    
    Args:
        chunk_df: DataFrame chunk để xử lý
        source_name: Tên file nguồn
        conn: Database connection
        
    Returns:
        Dict với số dòng inserted/updated
    """
    # Chuẩn hóa cột
    df = normalize_jsf_columns(chunk_df.copy())
    
    # Kiểm tra cột bắt buộc
    if 'so_ho_chieu' not in df.columns:
        return {"error": "Không tìm thấy cột 'Số hộ chiếu'", "inserted": 0, "updated": 0}
    
    # Chuẩn hóa passport
    df['so_ho_chieu'] = df['so_ho_chieu'].astype(str).apply(normalize_passport)
    df = df[df['so_ho_chieu'].astype(bool)]
    
    if df.empty:
        return {"inserted": 0, "updated": 0, "skipped": len(chunk_df)}
    
    # Chuẩn hóa các trường
    if 'ho_ten' in df.columns:
        df['ho_ten'] = df['ho_ten'].astype(str).str.strip().replace('nan', None)
    else:
        df['ho_ten'] = None
    
    if 'quoc_tich' in df.columns:
        df['quoc_tich'] = df['quoc_tich'].astype(str).str.strip().str.upper().replace('NAN', None)
    else:
        df['quoc_tich'] = None
    
    if 'dia_chi_tam_tru' in df.columns:
        df['dia_chi_tam_tru'] = df['dia_chi_tam_tru'].astype(str).str.replace(r'\n', ', ', regex=True).str.strip().replace('nan', None)
    else:
        df['dia_chi_tam_tru'] = None
    
    # Chuẩn hóa ngày
    df = normalize_jsf_dates(df)
    
    # Validation
    valid_rows = []
    validator = ImportValidator()
    records = df.to_dict('records')
    
    for idx, row in enumerate(records):
        validator.reset()
        validate_import_row(row, idx + 2, validator)
        if validator.get_result().is_valid:
            valid_rows.append(row)
    
    if not valid_rows:
        return {"inserted": 0, "updated": 0, "skipped": len(chunk_df)}
    
    # Tạo DataFrame từ valid rows
    df = pd.DataFrame(valid_rows)
    df['source_file'] = source_name
    
    # Chuẩn bị cột
    cols_to_keep = [
        'so_ho_chieu', 'ho_ten', 'ngay_sinh', 'quoc_tich', 'ngay_den',
        'ngay_di', 'dia_chi_tam_tru', 'source_file'
    ]
    
    if 'ket_qua_xac_minh' not in df.columns:
        df['ket_qua_xac_minh'] = None
    cols_to_keep.append('ket_qua_xac_minh')
    
    for col in cols_to_keep:
        if col not in df.columns:
            df[col] = None
    
    final_df = df[cols_to_keep]
    
    # Import vào database
    import uuid
    temp_table = f"temp_chunk_{uuid.uuid4().hex[:8]}"
    
    try:
        conn.register(temp_table, final_df)
        
        # Update existing
        conn.execute(f"""
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
            FROM {temp_table} t
            WHERE raw_immigration.so_ho_chieu = t.so_ho_chieu
              AND raw_immigration.ngay_den = t.ngay_den
        """)
        
        # Count updated
        updated_result = conn.execute(f"""
            SELECT COUNT(*) FROM raw_immigration r
            WHERE EXISTS (
                SELECT 1 FROM {temp_table} t
                WHERE r.so_ho_chieu = t.so_ho_chieu
                  AND r.ngay_den = t.ngay_den
            )
        """).fetchone()
        rows_updated = updated_result[0] if updated_result else 0
        
        # Insert new
        conn.execute(f"""
            INSERT INTO raw_immigration (
                so_ho_chieu, ho_ten, ngay_sinh, quoc_tich, ngay_den,
                ngay_di, dia_chi_tam_tru, ket_qua_xac_minh, source_file, thoi_diem_cap_nhat
            )
            SELECT
                t.so_ho_chieu, t.ho_ten, t.ngay_sinh, t.quoc_tich, t.ngay_den,
                t.ngay_di, t.dia_chi_tam_tru, t.ket_qua_xac_minh, t.source_file, CURRENT_TIMESTAMP
            FROM {temp_table} t
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_immigration r
                WHERE r.so_ho_chieu = t.so_ho_chieu
                  AND r.ngay_den = t.ngay_den
            )
        """)
        
        rows_inserted = len(final_df) - rows_updated
        conn.commit()
        
        return {"inserted": rows_inserted, "updated": rows_updated, "skipped": len(chunk_df) - len(final_df)}
        
    finally:
        try:
            conn.unregister(temp_table)
        except Exception:
            pass


from typing import Callable

def import_jsf_chunked(
    file_path: str, 
    progress_callback: Callable[[float, str], None] = None,
    chunk_size: int = None
) -> Dict[str, Any]:
    """
    Import JSF với chunk processing cho file lớn.
    Chia file thành các chunks và import từng phần với progress callback.
    
    Args:
        file_path: Đường dẫn file JSF
        progress_callback: Callback function(progress: float, message: str)
                          progress từ 0.0 đến 1.0
        chunk_size: Số dòng mỗi chunk (default: CHUNK_SIZE = 5000)
        
    Returns:
        Dict với kết quả import tổng hợp
    """
    if chunk_size is None:
        chunk_size = CHUNK_SIZE
    
    # 1. Trích xuất toàn bộ dữ liệu từ JSF
    if progress_callback:
        progress_callback(0.0, "Đang đọc file JSF...")
    
    df = extract_jsf_data(file_path)
    
    if df is None or df.empty:
        return {
            "success": False,
            "error": "Không thể đọc dữ liệu từ file JSF hoặc file trống",
            "rows_imported": 0,
            "rows_skipped": 0
        }
    
    total_rows = len(df)
    source_name = Path(file_path).name
    
    if progress_callback:
        progress_callback(0.1, f"Đã đọc {total_rows:,} dòng, bắt đầu import...")
    
    # 2. Nếu file nhỏ, dùng import thông thường
    if total_rows <= chunk_size:
        if progress_callback:
            progress_callback(0.5, "File nhỏ, import trực tiếp...")
        result = import_jsf(file_path)
        if progress_callback:
            progress_callback(1.0, "Hoàn thành!")
        return result
    
    # 3. Chia thành chunks và import
    conn = get_connection()
    total_chunks = (total_rows + chunk_size - 1) // chunk_size
    
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    errors = []
    
    for i, chunk_start in enumerate(range(0, total_rows, chunk_size)):
        chunk_end = min(chunk_start + chunk_size, total_rows)
        chunk_df = df.iloc[chunk_start:chunk_end]
        
        # Cập nhật progress
        if progress_callback:
            progress = 0.1 + (0.85 * (i + 1) / total_chunks)
            progress_callback(
                progress, 
                f"Đang xử lý chunk {i + 1}/{total_chunks} ({chunk_end:,}/{total_rows:,} dòng)..."
            )
        
        # Import chunk
        try:
            chunk_result = _process_and_import_chunk(chunk_df, source_name, conn)
            total_inserted += chunk_result.get("inserted", 0)
            total_updated += chunk_result.get("updated", 0)
            total_skipped += chunk_result.get("skipped", 0)
            
            if chunk_result.get("error"):
                errors.append(f"Chunk {i + 1}: {chunk_result['error']}")
                
        except Exception as e:
            errors.append(f"Chunk {i + 1}: {str(e)}")
    
    if progress_callback:
        progress_callback(1.0, "Hoàn thành!")
    
    try:
        st.cache_data.clear()
    except Exception:
        pass

    return {
        "success": len(errors) == 0,
        "rows_imported": total_inserted + total_updated,
        "rows_inserted": total_inserted,
        "rows_updated": total_updated,
        "rows_skipped": total_skipped,
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "errors": errors if errors else None,
        "source_file": source_name
    }

