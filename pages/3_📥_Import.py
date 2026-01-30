"""
QLNNN Offline - Trang Import dữ liệu
Import từ Excel/CSV (Admin only)
"""

import streamlit as st
from pathlib import Path
import sys
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.import_data import import_excel, import_csv, import_verification_results
from modules.export_data import generate_template
from database.connection import get_table_count

st.set_page_config(page_title="Import - QLNNN", page_icon="📥", layout="wide")

# Auth check
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Vui lòng đăng nhập")
    st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("⛔ Chức năng này chỉ dành cho Admin")
    st.stop()

st.title("📥 Import dữ liệu")

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    try:
        st.metric("📊 Bản ghi hiện tại", f"{get_table_count('raw_immigration'):,}")
    except:
        st.metric("📊 Bản ghi", "N/A")
with col2:
    try:
        st.metric("💼 Lao động", get_table_count("ref_labor"))
    except:
        pass
with col3:
    try:
        st.metric("⚠️ Đối tượng chú ý", get_table_count("ref_watchlist"))
    except:
        pass

st.markdown("---")

# File upload
st.markdown("### 📋 Import dữ liệu NNN")
uploaded_file = st.file_uploader("Chọn file Excel/CSV", type=["xlsx", "xls", "csv"])

if uploaded_file:
    st.info(f"📁 File: **{uploaded_file.name}**")
    
    if st.button("📤 Import", type="primary"):
        with st.spinner("Đang import..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                if uploaded_file.name.endswith('.csv'):
                    result = import_csv(tmp_path)
                else:
                    result = import_excel(tmp_path)
                
                if result["success"]:
                    st.success(f"✅ Đã import **{result['rows_imported']}** dòng")
                    st.cache_data.clear()
                    st.toast("🧹 Đã xóa cache dữ liệu cũ", icon="🧹")
                else:
                    st.error(f"❌ Lỗi: {result['error']}")
            finally:
                os.unlink(tmp_path)
