"""
QLNNN Offline - Trang Import dữ liệu
Import từ Excel/CSV/JSF (Admin only)
"""

import streamlit as st
from pathlib import Path
import sys
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.import_data import import_excel, import_csv, import_verification_results
from modules.import_jsf import import_jsf
from modules.export_data import generate_template
from database.connection import get_table_count
from utils.menu import menu

st.set_page_config(page_title="Nhập liệu - QLNNN", page_icon="📥", layout="wide")

# Auth check
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Vui lòng đăng nhập")
    st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("⛔ Chức năng này chỉ dành cho Admin")
    st.stop()

menu()

st.title("📥 Nhập liệu hệ thống")

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    try:
        st.metric("📊 Bản ghi hiện tại", f"{get_table_count('raw_immigration'):,}")
    except (ValueError, Exception) as e:
        st.metric("📊 Bản ghi", "N/A")
with col2:
    try:
        st.metric("💼 Lao động", get_table_count("ref_labor"))
    except (ValueError, Exception):
        st.metric("💼 Lao động", "N/A")
with col3:
    try:
        st.metric("⚠️ Đối tượng chú ý", get_table_count("ref_watchlist"))
    except (ValueError, Exception):
        st.metric("⚠️ Đối tượng chú ý", "N/A")

st.markdown("---")

# File upload
st.markdown("### 📋 Upload file dữ liệu")
st.caption("Hỗ trợ: Excel (.xlsx, .xls), CSV (.csv), và **JSF/PDF** (.jsf, .pdf)")

uploaded_file = st.file_uploader(
    "Chọn file dữ liệu", 
    type=["xlsx", "xls", "csv", "pdf", "jsf"],
    help="File JSF là báo cáo tạm trú người nước ngoài từ hệ thống PA61"
)

if uploaded_file:
    file_ext = Path(uploaded_file.name).suffix.lower()
    
    # Hiển thị thông tin file
    if file_ext in ['.pdf', '.jsf']:
        st.info(f"📄 File JSF: **{uploaded_file.name}** - Sẽ dùng pdfplumber để trích xuất")
    else:
        st.info(f"📁 File: **{uploaded_file.name}**")
    
    if st.button("📤 Tiến hành nhập liệu", type="primary"):
        with st.spinner("Đang xử lý dữ liệu..."):
            # Xác định suffix cho temp file
            suffix = file_ext if file_ext else '.tmp'
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                # Xử lý theo loại file
                if file_ext in ['.pdf', '.jsf']:
                    result = import_jsf(tmp_path)
                elif file_ext == '.csv':
                    result = import_csv(tmp_path)
                else:
                    result = import_excel(tmp_path)
                
                if result["success"]:
                    # Hiển thị kết quả chi tiết
                    st.success(f"✅ Import thành công!")
                    
                    # Thống kê
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("📊 Tổng import", result.get('rows_imported', 0))
                    with col_b:
                        if 'rows_inserted' in result:
                            st.metric("➕ Mới thêm", result.get('rows_inserted', 0))
                        elif 'rows_updated' in result:
                            st.metric("🔄 Cập nhật", result.get('rows_updated', 0))
                    with col_c:
                        st.metric("⏭️ Bỏ qua", result.get('rows_skipped', 0))
                    
                    # Báo cáo validation nếu có warnings
                    if result.get('validation_report'):
                        report = result['validation_report']
                        if report.get('total_warnings', 0) > 0:
                            with st.expander(f"⚠️ {report['total_warnings']} cảnh báo validation"):
                                for detail in report.get('details', [])[:10]:
                                    for w in detail.get('warnings', []):
                                        st.warning(f"Dòng {w.get('row')}: {w.get('message')}")
                else:
                    st.error(f"❌ Lỗi: {result.get('error', 'Unknown error')}")
                    
                    # Hiển thị chi tiết lỗi validation nếu có
                    if result.get('validation_report'):
                        report = result['validation_report']
                        if report.get('total_errors', 0) > 0:
                            with st.expander(f"🔍 Chi tiết lỗi ({report['total_errors']} lỗi)"):
                                for detail in report.get('details', [])[:10]:
                                    for e in detail.get('errors', []):
                                        st.error(f"Dòng {e.get('row')}, cột {e.get('column')}: {e.get('message')}")
            finally:
                os.unlink(tmp_path)

