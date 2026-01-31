#!/usr/bin/env python3
"""
Test script - Import JSF file to Excel
Based on pdf_to_sheets.py logic
"""

import os
import sys
import io
import pandas as pd
import pdfplumber

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ===== CẤU HÌNH =====
BASE_DIR = os.path.dirname(os.path.realpath(__file__)) if '__file__' in globals() else os.getcwd()
OUTPUT_DIR = os.path.join(BASE_DIR, 'Output')

# Tạo thư mục Output nếu chưa có
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_jsf_to_excel(file_path: str) -> str:
    """
    Trích xuất dữ liệu từ file JSF thành Excel.
    
    Args:
        file_path: Đường dẫn file JSF
        
    Returns:
        Đường dẫn file Excel đã tạo
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base_name}_extracted.xlsx")
    all_dfs = []
    
    print(f"📂 Đang đọc file: {os.path.basename(file_path)}")
    
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"📄 Số trang: {total_pages}")
            
            if not pdf.pages:
                print(f"⚠️ File {os.path.basename(file_path)} không có dữ liệu")
                return None
            
            for i, page in enumerate(pdf.pages, 1):
                print(f"🔄 Đang xử lý trang {i}/{total_pages}...", end='\r')
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
            
            print()  # New line sau progress
            
    except Exception as e:
        print(f"❌ Lỗi đọc file {os.path.basename(file_path)}: {e}")
        return None

    if not all_dfs:
        print(f"⚠️ Không tìm thấy bảng trong {os.path.basename(file_path)}")
        return None

    # Ghép tất cả bảng
    df_all = pd.concat(all_dfs, ignore_index=True)
    print(f"📊 Tổng số dòng raw: {len(df_all)}")
    
    # Hiển thị cột
    print(f"📋 Các cột: {list(df_all.columns)}")

    # Làm sạch cột STT - loại bỏ dòng không phải số
    if 'STT' in df_all.columns:
        before = len(df_all)
        df_all = df_all[pd.to_numeric(df_all['STT'], errors='coerce').notna()]
        after = len(df_all)
        if before != after:
            print(f"🧹 Loại bỏ {before - after} dòng không hợp lệ (không có STT)")

    # Chuẩn hóa ngày tháng
    date_columns = ['Ngày sinh', 'Ngày đến', 'Ngày đi']
    for col in date_columns:
        if col in df_all.columns:
            print(f"📅 Chuẩn hóa: {col}")
            # Giữ nguyên định dạng DD/MM/YYYY
            datetime_col = pd.to_datetime(df_all[col], dayfirst=True, errors='coerce')
            df_all[col] = datetime_col.apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '')

    # Lưu Excel
    df_all.to_excel(out_path, index=False)
    print(f"✅ Tạo Excel: {os.path.basename(out_path)}")
    print(f"📊 Số dòng: {len(df_all)}")
    print(f"📂 Đường dẫn: {out_path}")
    
    # Preview 5 dòng đầu
    print("\n📋 Preview 5 dòng đầu:")
    print(df_all.head().to_string())
    
    return out_path


if __name__ == '__main__':
    # File JSF cần test
    jsf_file = os.path.join(BASE_DIR, '30.01.jsf')
    
    if not os.path.exists(jsf_file):
        print(f"❌ Không tìm thấy file: {jsf_file}")
    else:
        result = extract_jsf_to_excel(jsf_file)
        if result:
            print(f"\n🎉 Hoàn thành! File Excel: {result}")
        else:
            print("\n❌ Không thể tạo file Excel")
    
    input("\nNhấn Enter để thoát...")
