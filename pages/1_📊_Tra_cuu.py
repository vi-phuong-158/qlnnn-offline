"""
QLNNN Offline - Trang Tra cứu
Tra cứu đơn và hàng loạt
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.search import search_single, search_batch, search_batch_all, get_not_found
from modules.export_data import export_to_xlsx
from utils.text_utils import split_passports, normalize_passport
from utils.date_utils import format_date_vn
from config import STATUS_COLORS, PAGE_SIZE

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Tra cứu - QLNNN",
    page_icon="🔍",
    layout="wide"
)

# Check authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Vui lòng đăng nhập để sử dụng chức năng này")
    st.page_link("app.py", label="← Về trang đăng nhập")
    st.stop()

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_status_class(status: str) -> str:
    """Get CSS class based on status"""
    if status == "Đối tượng chú ý":
        return "watchlist"
    elif status == "Lao động":
        return "labor"
    elif status == "Kết hôn":
        return "marriage"
    elif status == "Học tập":
        return "student"
    return ""


def render_result_card(record: dict):
    """Render a single result card"""
    status = record.get("trang_thai_cuoi_cung", "")
    status_class = get_status_class(status)
    
    # Color coding
    border_color = STATUS_COLORS.get(status, STATUS_COLORS["default"])
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding-left: 1rem; margin-bottom: 1rem;">
                <h4 style="margin: 0;">{record.get('ho_ten', 'N/A')}</h4>
                <p style="color: #666; margin: 0.25rem 0;">
                    🛂 {record.get('so_ho_chieu', 'N/A')} | 
                    🌍 {record.get('quoc_tich', 'N/A')} |
                    🎂 {format_date_vn(record.get('ngay_sinh', ''))}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if status:
                st.markdown(f"""
                <span style="background-color: {border_color}; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem;">
                    {status}
                </span>
                """, unsafe_allow_html=True)
        
        # Details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            **📅 Ngày đến:** {format_date_vn(record.get('ngay_den', ''))}  
            **📅 Ngày đi:** {format_date_vn(record.get('ngay_di', '')) or '(Chưa đi)'}
            """)
        
        with col2:
            st.markdown(f"""
            **🔢 Số lần NC:** {record.get('so_lan_nhap_canh', 0)}  
            **📊 Tổng ngày (năm):** {record.get('tong_ngay_luu_tru_2025', 0)}
            """)
        
        with col3:
            st.markdown(f"""
            **📊 Tổng ngày (tích lũy):** {record.get('tong_ngay_tich_luy', 0)}  
            **✅ Xác minh:** {record.get('ket_qua_xac_minh', '') or 'Chưa có'}
            """)
        
        # Address
        if record.get('dia_chi_tam_tru'):
            st.markdown(f"**📍 Địa chỉ:** {record.get('dia_chi_tam_tru')}")
        
        # Detail tooltips
        if status == "Lao động" and record.get('labor_detail'):
            st.info(f"💼 {record.get('labor_detail')}")
        elif status == "Kết hôn" and record.get('marriage_detail'):
            st.success(f"💒 {record.get('marriage_detail')}")
        elif status == "Đối tượng chú ý" and record.get('watchlist_detail'):
            st.error(f"⚠️ {record.get('watchlist_detail')}")
        
        st.markdown("---")


# ============================================
# PAGE CONTENT
# ============================================

st.title("🔍 Tra cứu người nước ngoài")

# Tabs for different search modes
tab1, tab2 = st.tabs(["📝 Tra cứu đơn", "📋 Tra cứu hàng loạt"])

# ============================================
# TAB 1: Single Search
# ============================================

with tab1:
    st.markdown("### Tìm kiếm theo số hộ chiếu hoặc họ tên")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        keyword = st.text_input(
            "Từ khóa tìm kiếm",
            placeholder="Nhập số hộ chiếu hoặc họ tên...",
            label_visibility="collapsed"
        )
    
    with col2:
        search_btn = st.button("🔍 Tìm kiếm", use_container_width=True, type="primary")
    
    if search_btn and keyword:
        with st.spinner("Đang tìm kiếm..."):
            results = search_single(keyword)
        
        if results:
            st.success(f"✅ Tìm thấy {len(results)} kết quả")
            
            # Export button
            if st.button("📥 Xuất Excel"):
                file_path = export_to_xlsx(results)
                with open(file_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Tải file Excel",
                        data=f,
                        file_name=file_path,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            # Render results
            for record in results:
                render_result_card(record)
        else:
            st.warning("❌ Không tìm thấy kết quả nào")
    
    elif search_btn:
        st.warning("Vui lòng nhập từ khóa tìm kiếm")


# ============================================
# TAB 2: Batch Search
# ============================================

with tab2:
    st.markdown("### Tra cứu hàng loạt (tối đa 1000 số hộ chiếu)")
    st.caption("Nhập danh sách số hộ chiếu, phân cách bằng dấu phẩy, xuống dòng hoặc khoảng trắng")
    
    # Session state for pagination
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = None
        st.session_state.batch_keywords = []
        st.session_state.batch_offset = 0
    
    batch_input = st.text_area(
        "Danh sách số hộ chiếu",
        height=150,
        placeholder="E1234567\nE2345678\nE3456789\n...",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        batch_search_btn = st.button("📋 Tra cứu hàng loạt", type="primary", use_container_width=True)
    
    if batch_search_btn and batch_input:
        keywords = split_passports(batch_input)
        
        if not keywords:
            st.warning("Không tìm thấy số hộ chiếu hợp lệ trong danh sách")
        else:
            st.info(f"📝 Đang tra cứu {len(keywords)} số hộ chiếu...")
            
            with st.spinner("Đang tìm kiếm..."):
                result = search_batch(keywords, limit=PAGE_SIZE, offset=0)
            
            st.session_state.batch_results = result
            st.session_state.batch_keywords = keywords
            st.session_state.batch_offset = 0
    
    # Display batch results
    if st.session_state.batch_results:
        result = st.session_state.batch_results
        total = result["total"]
        records = result["results"]
        has_more = result["hasMore"]
        
        st.success(f"✅ Tìm thấy {total} kết quả")
        
        # Not found passports
        if records:
            found_passports = [r["so_ho_chieu"] for r in records]
            not_found = get_not_found(st.session_state.batch_keywords, found_passports)
            
            if not_found:
                with st.expander(f"⚠️ {len(not_found)} số hộ chiếu không tìm thấy"):
                    st.write(", ".join(not_found[:50]))
                    if len(not_found) > 50:
                        st.write(f"...và {len(not_found) - 50} số khác")
        
        # Export all button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📥 Xuất tất cả Excel"):
                with st.spinner("Đang tải toàn bộ dữ liệu..."):
                    all_results = search_batch_all(st.session_state.batch_keywords)
                    file_path = export_to_xlsx(all_results)
                    
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Tải file Excel",
                            data=f,
                            file_name=file_path,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
        
        # Render results
        st.markdown("---")
        
        for record in records:
            render_result_card(record)
        
        # Load more button
        if has_more:
            if st.button("⬇️ Tải thêm kết quả"):
                new_offset = st.session_state.batch_offset + PAGE_SIZE
                
                with st.spinner("Đang tải thêm..."):
                    more_results = search_batch(
                        st.session_state.batch_keywords,
                        limit=PAGE_SIZE,
                        offset=new_offset
                    )
                
                # Append results
                st.session_state.batch_results["results"].extend(more_results["results"])
                st.session_state.batch_results["hasMore"] = more_results["hasMore"]
                st.session_state.batch_offset = new_offset
                
                st.rerun()
        else:
            st.info("📌 Đã hiển thị tất cả kết quả")


# ============================================
# SIDEBAR INFO
# ============================================

with st.sidebar:
    st.markdown("### 💡 Mẹo tra cứu")
    st.markdown("""
    - **Số hộ chiếu**: Nhập chính xác (VD: E1234567)
    - **Họ tên**: Có thể viết không dấu
    - **Hàng loạt**: Copy paste từ Excel
    
    ---
    
    ### 🎨 Ý nghĩa màu sắc
    
    🔴 **Đỏ**: Đối tượng chú ý  
    🟡 **Vàng**: Lao động  
    🟢 **Xanh lá**: Kết hôn  
    🔵 **Xanh dương**: Học tập  
    ⚪ **Xám**: Chưa xác định
    """)
