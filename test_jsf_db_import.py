#!/usr/bin/env python3
"""
Test script - Import JSF file to database
Test lọc trùng và validation
"""

import os
import sys
import io
from pathlib import Path

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from modules.import_jsf import import_jsf, extract_jsf_data
from database.connection import get_connection, get_table_count

# ===== CẤU HÌNH =====
BASE_DIR = os.path.dirname(os.path.realpath(__file__)) if '__file__' in globals() else os.getcwd()


def test_import_jsf():
    """Test import JSF vào database"""
    jsf_file = os.path.join(BASE_DIR, '30.01.jsf')
    
    if not os.path.exists(jsf_file):
        print(f"❌ Không tìm thấy file: {jsf_file}")
        return
    
    print("=" * 60)
    print("🧪 TEST IMPORT JSF VÀO DATABASE")
    print("=" * 60)
    
    # Thống kê trước import
    try:
        count_before = get_table_count('raw_immigration')
        print(f"📊 Số bản ghi TRƯỚC import: {count_before:,}")
    except Exception as e:
        count_before = 0
        print(f"⚠️ Không thể đếm bản ghi: {e}")
    
    print(f"\n📂 File: {os.path.basename(jsf_file)}")
    print("🔄 Đang import...")
    
    # Import
    result = import_jsf(jsf_file)
    
    print("\n📋 KẾT QUẢ:")
    print("-" * 40)
    
    if result['success']:
        print(f"✅ Thành công!")
        print(f"   📊 Tổng xử lý: {result.get('rows_imported', 0)}")
        print(f"   ➕ Thêm mới: {result.get('rows_inserted', 0)}")
        print(f"   🔄 Cập nhật: {result.get('rows_updated', 0)}")
        print(f"   ⏭️ Bỏ qua: {result.get('rows_skipped', 0)}")
        
        # Thống kê sau import
        try:
            count_after = get_table_count('raw_immigration')
            print(f"\n📊 Số bản ghi SAU import: {count_after:,}")
            print(f"📈 Tăng thêm: {count_after - count_before:,}")
        except Exception:
            pass
        
        # Validation report
        if result.get('validation_report'):
            report = result['validation_report']
            if report.get('total_warnings', 0) > 0:
                print(f"\n⚠️ Cảnh báo validation: {report['total_warnings']}")
    else:
        print(f"❌ Thất bại: {result.get('error', 'Unknown error')}")
        
        if result.get('validation_report'):
            report = result['validation_report']
            print(f"   🔍 Lỗi: {report.get('total_errors', 0)}")
            for detail in report.get('details', [])[:5]:
                for e in detail.get('errors', []):
                    print(f"      - Dòng {e.get('row')}: {e.get('message')}")
    
    print("\n" + "=" * 60)


def test_duplicate_detection():
    """Test chạy import lần 2 để kiểm tra logic lọc trùng"""
    jsf_file = os.path.join(BASE_DIR, '30.01.jsf')
    
    if not os.path.exists(jsf_file):
        return
    
    print("\n🔄 TEST LỌC TRÙNG - Import lần 2 cùng file...")
    
    result = import_jsf(jsf_file)
    
    if result['success']:
        print(f"✅ Kết quả lần 2:")
        print(f"   ➕ Thêm mới: {result.get('rows_inserted', 0)} (nên = 0)")
        print(f"   🔄 Cập nhật: {result.get('rows_updated', 0)} (nên = tổng import)")
        
        if result.get('rows_inserted', 0) == 0:
            print("✅ PASS: Logic lọc trùng hoạt động đúng!")
        else:
            print("❌ FAIL: Có bản ghi trùng vẫn được thêm mới")
    else:
        print(f"❌ Import lần 2 thất bại: {result.get('error')}")


if __name__ == '__main__':
    test_import_jsf()
    test_duplicate_detection()
    
    input("\nNhấn Enter để thoát...")
