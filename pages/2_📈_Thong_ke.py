"""
QLNNN Offline - Trang Thống kê
Báo cáo và phân tích dữ liệu
"""

import streamlit as st
from pathlib import Path
from datetime import date, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.statistics import (
    get_statistics, get_statistics_by_nationality,
    get_person_list, generate_narrative, get_last_update_time,
    get_ml_predictions, generate_narrative_by_purpose, get_matrix_report
)
from modules.export_data import export_statistics_to_xlsx
from utils.date_utils import format_date_vn
from config import CONTINENT_RULES, PAGE_SIZE

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Thống kê - QLNNN",
    page_icon="📈",
    layout="wide"
)

# Check authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Vui lòng đăng nhập để sử dụng chức năng này")
    st.page_link("app.py", label="← Về trang đăng nhập")
    st.stop()

# ============================================
# PAGE CONTENT
# ============================================

st.title("📈 Thống kê & Phân tích")

# Last update info
last_update = get_last_update_time()
st.info(f"📅 Dữ liệu cập nhật lần cuối: **{last_update}**")

# ============================================
# FILTERS
# ============================================

st.markdown("### 🔧 Bộ lọc")

# Filter Mode Toggle
filter_mode = st.radio(
    "Chế độ lọc",
    options=["Theo thời gian đến (Date of Arrival)", "Theo tổng ngày lưu trú (Total Days)"],
    horizontal=True,
    label_visibility="collapsed"
)

col1, col2, col3, col4 = st.columns(4)

date_from_str = None
date_to_str = None
min_days_val = None

# Column 1 & 2: Date or Days Input
if filter_mode == "Theo thời gian đến (Date of Arrival)":
    with col1:
        default_from = date.today() - timedelta(days=30)
        date_from = st.date_input("Từ ngày", value=default_from, format="DD/MM/YYYY")
    with col2:
        date_to = st.date_input("Đến ngày", value=date.today(), format="DD/MM/YYYY")
    
    date_from_str = date_from.strftime("%Y-%m-%d") if date_from else None
    date_to_str = date_to.strftime("%Y-%m-%d") if date_to else None
else:
    with col1:
        min_days_val = st.number_input(
            "Tổng ngày lưu trú (từ... trở lên)", 
            min_value=1, 
            value=180,
            step=1,
            help="Lọc những người có tổng số ngày lưu trú trong năm 2025 lớn hơn hoặc bằng số này. Bỏ qua lọc theo ngày đến."
        )
    with col2:
        st.info("Đang lọc theo tổng ngày lưu trú")

# Column 3 & 4: Continent & Status
with col3:
    continent_options = ["ALL", "ASIA_OCEANIA"] + list(CONTINENT_RULES.keys())
    continent_labels = {
        "ALL": "Tất cả châu lục",
        "ASIA_OCEANIA": "Châu Á & Châu Đại Dương",
        "ASIA": "Châu Á",
        "EUROPE": "Châu Âu",
        "AMERICA": "Châu Mỹ",
        "OCEANIA": "Châu Đại Dương",
        "AFRICA": "Châu Phi"
    }
    continent = st.multiselect(
        "Châu lục",
        options=continent_options,
        default=["ALL"],
        format_func=lambda x: continent_labels.get(x, x)
    )

with col4:
    status_options = [None, "Lao động", "Kết hôn", "Học tập", "Đối tượng chú ý"]
    residence_status = st.selectbox(
        "Mục đích",
        options=status_options,
        format_func=lambda x: x if x else "Tất cả"
    )

# Additional filters (Hidden day filter since we have main toggle, keeps others if any)
col1, col2, col3, col4 = st.columns(4)
with col4:
    filter_btn = st.button("🔄 Áp dụng bộ lọc", type="primary", use_container_width=True)

st.markdown("---")

# ============================================
# STATISTICS DISPLAY
# ============================================

# Get statistics
stats = get_statistics(
    date_from=date_from_str,
    date_to=date_to_str,
    continent=continent,
    residence_status=residence_status,
    min_days=min_days_val
)

# Summary cards
st.markdown("### 📊 Tổng quan")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="👥 Tổng số người",
        value=f"{stats['total_persons']:,}"
    )

with col2:
    st.metric(
        label="🌍 Số quốc tịch",
        value=stats['total_nationalities']
    )

with col3:
    st.metric(
        label="🏠 Đang lưu trú",
        value=f"{stats['currently_residing']:,}"
    )

with col4:
    st.metric(
        label="📊 TB ngày lưu trú",
        value=f"{stats['avg_days']} ngày"
    )

# Purpose breakdown
st.markdown("### 📋 Phân loại theo mục đích")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💼 Lao động",
        value=stats['labor_count']
    )

with col2:
    st.metric(
        label="💒 Kết hôn",
        value=stats['marriage_count']
    )

with col3:
    st.metric(
        label="📚 Học tập",
        value=stats['student_count']
    )

with col4:
    st.metric(
        label="⚠️ Đối tượng chú ý",
        value=stats['watchlist_count'],
        delta="Cần theo dõi" if stats['watchlist_count'] > 0 else None,
        delta_color="inverse"
    )

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Văn bản tường thuật", "🌍 Theo quốc tịch", "📋 Danh sách chi tiết", "🎯 Dự đoán mục đích", "📊 Ma trận"])

# ============================================
# TAB 1: Narrative Text
# ============================================

with tab1:
    st.markdown("### 📝 Văn bản thống kê")
    
    # Choose narrative type
    narrative_type = st.radio(
        "Loại tường thuật",
        options=["Tổng quan", "Theo mục đích"],
        horizontal=True
    )
    
    if narrative_type == "Tổng quan":
        narrative = generate_narrative(
            date_from=date_from_str,
            date_to=date_to_str,
            continent=continent,
            residence_status=residence_status,
            min_days=min_days_val
        )
    else:
        # Tường thuật theo mục đích (Lao động, Thăm thân) - giống GAS gốc
        narrative = generate_narrative_by_purpose(
            date_from=date_from_str,
            date_to=date_to_str,
            continent=continent,
            residence_status="dang_tam_tru" if st.checkbox("Chỉ người đang tạm trú") else None,
            min_days=min_days_val
        )
        if not narrative:
            narrative = "Không có dữ liệu phù hợp với bộ lọc."
    
    st.markdown(narrative)
    
    # Copy button
    st.text_area(
        "Copy văn bản",
        value=narrative.replace("**", ""),
        height=200,
        label_visibility="collapsed"
    )

# ============================================
# TAB 2: By Nationality
# ============================================

with tab2:
    st.markdown("### 🌍 Thống kê theo quốc tịch")
    
    by_nationality = get_statistics_by_nationality(
        date_from=date_from_str,
        date_to=date_to_str,
        continent=continent,
        min_days=min_days_val,
        limit=50
    )
    
    if by_nationality:
        import pandas as pd
        import plotly.express as px
        
        df = pd.DataFrame(by_nationality)
        df.columns = ["Quốc tịch", "Số lượng", "Đang lưu trú"]
        
        # Summary stats
        total_people = df["Số lượng"].sum()
        total_countries = len(df)
        total_residing = df["Đang lưu trú"].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Tổng số người", f"{total_people:,}")
        with col2:
            st.metric("🌍 Số quốc tịch", total_countries)
        with col3:
            st.metric("🏠 Đang lưu trú", f"{total_residing:,}")
        
        st.markdown("---")
        
        # Charts side by side
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Biểu đồ cột")
            chart_data = df.head(10).copy()
            fig_bar = px.bar(
                chart_data,
                x="Quốc tịch",
                y="Số lượng",
                color="Đang lưu trú",
                title="Top 10 quốc tịch",
                color_continuous_scale="Blues"
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            st.markdown("#### 🥧 Biểu đồ tròn")
            pie_data = df.head(10).copy()
            # Add "Khác" for remaining
            if len(df) > 10:
                other_count = df.iloc[10:]["Số lượng"].sum()
                pie_data = pd.concat([pie_data, pd.DataFrame([{"Quốc tịch": "Khác", "Số lượng": other_count, "Đang lưu trú": 0}])], ignore_index=True)
            
            fig_pie = px.pie(
                pie_data,
                values="Số lượng",
                names="Quốc tịch",
                title="Tỷ lệ theo quốc tịch"
            )
            fig_pie.update_layout(height=400)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        
        # Table
        st.markdown("#### 📋 Danh sách chi tiết")
        df.index = df.index + 1
        df.index.name = "STT"
        
        # Add percentage column
        df["Tỷ lệ %"] = (df["Số lượng"] / total_people * 100).round(2)
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=False
        )
    else:
        st.info("Không có dữ liệu")

# ============================================
# TAB 3: Person List
# ============================================

with tab3:
    st.markdown("### 📋 Danh sách chi tiết")
    
    # Session state for pagination
    if "stats_offset" not in st.session_state:
        st.session_state.stats_offset = 0
    
    result = get_person_list(
        date_from=date_from_str,
        date_to=date_to_str,
        continent=continent,
        residence_status=residence_status,
        min_days=min_days_val,
        limit=PAGE_SIZE,
        offset=st.session_state.stats_offset
    )
    
    total = result["total"]
    records = result["results"]
    has_more = result["hasMore"]
    
    st.write(f"Tổng cộng: **{total:,}** người")
    
    # Export button
    if st.button("📥 Xuất Excel (toàn bộ)"):
        with st.spinner("Đang xuất dữ liệu..."):
            # Get all data
            all_result = get_person_list(
                date_from=date_from_str,
                date_to=date_to_str,
                continent=continent,
                residence_status=residence_status,
                min_days=min_days_val,
                limit=10000,
                offset=0
            )
            
            filters = {
                "Từ ngày": format_date_vn(date_from_str) if date_from_str else "",
                "Đến ngày": format_date_vn(date_to_str) if date_to_str else "",
                "Châu lục": continent_labels.get(continent, continent),
                "Mục đích": residence_status or "Tất cả"
            }
            
            file_path = export_statistics_to_xlsx(
                stats=stats,
                by_nationality=by_nationality,
                person_list=all_result["results"],
                filters=filters
            )
            
            with open(file_path, "rb") as f:
                st.download_button(
                    label="⬇️ Tải file Excel",
                    data=f,
                    file_name=file_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Display table
    if records:
        import pandas as pd
        
        df = pd.DataFrame(records)
        
        # Select and rename columns
        display_cols = {
            "ho_ten": "Họ tên",
            "quoc_tich": "Quốc tịch",
            "so_ho_chieu": "Số hộ chiếu",
            "ngay_den": "Ngày đến",
            "ngay_di": "Ngày đi",
            "tong_ngay_luu_tru_2025": "Tổng ngày",
            "trang_thai_cuoi_cung": "Mục đích"
        }
        
        df_display = df[[c for c in display_cols.keys() if c in df.columns]]
        df_display.columns = [display_cols[c] for c in df_display.columns]
        
        # Format dates
        for col in ["Ngày đến", "Ngày đi"]:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: format_date_vn(x) if x else ""
                )
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Pagination
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            if st.session_state.stats_offset > 0:
                if st.button("← Trang trước"):
                    st.session_state.stats_offset -= PAGE_SIZE
                    st.rerun()
        
        with col2:
            current_page = (st.session_state.stats_offset // PAGE_SIZE) + 1
            total_pages = (total // PAGE_SIZE) + (1 if total % PAGE_SIZE else 0)
            st.write(f"Trang {current_page} / {total_pages}")
        
        with col3:
            if has_more:
                if st.button("Trang sau →"):
                    st.session_state.stats_offset += PAGE_SIZE
                    st.rerun()
    else:
        st.info("Không có dữ liệu")

# ============================================
# TAB 4: ML Predictions
# ============================================

with tab4:
    st.markdown("### 🎯 Dự đoán mục đích (Rule-based ML)")
    
    st.info("""
    **Quy tắc tính điểm rủi ro:**
    - 📍 Địa chỉ: KCN/CCN (+3), Công ty/Cty (+2), Homestay/Resort (+1)
    - ⏱️ Thời gian: ≥90 ngày (+3), ≥30 ngày (+2), ≥8 ngày (+1)
    - 🔄 Số lần nhập cảnh: ≥5 lần (+2), ≥3 lần (+1)
    - 🎯 Mục đích: Lao động (+2), Kết hôn/Thăm thân (+1)
    """)
    
    # Risk level filter
    col1, col2 = st.columns([1, 3])
    with col1:
        risk_filter = st.selectbox(
            "Mức rủi ro",
            options=[None, "HIGH", "MEDIUM", "LOW"],
            format_func=lambda x: {
                None: "Tất cả",
                "HIGH": "🔴 Cao (≥6 điểm)",
                "MEDIUM": "🟡 Trung bình (3-5 điểm)",
                "LOW": "🟢 Thấp (<3 điểm)"
            }.get(x, x)
        )
    
    # Get predictions
    predictions = get_ml_predictions(risk_level=risk_filter, limit=100)
    
    if predictions:
        import pandas as pd
        
        df_pred = pd.DataFrame(predictions)
        
        # Select display columns
        display_cols = {
            "ho_ten": "Họ tên",
            "so_ho_chieu": "Số hộ chiếu",
            "quoc_tich": "Quốc tịch",
            "tong_ngay_luu_tru_2025": "Tổng ngày",
            "so_lan_nhap_canh": "Số lần NC",
            "risk_score": "Điểm",
            "risk_level_calc": "Mức",
            "prediction_reason": "Lý do"
        }
        
        df_display = df_pred[[c for c in display_cols.keys() if c in df_pred.columns]]
        df_display.columns = [display_cols[c] for c in df_display.columns]
        
        # Color code by risk level
        def color_risk(val):
            if val == "HIGH":
                return "background-color: #ffcccc"
            elif val == "MEDIUM":
                return "background-color: #fff3cd"
            elif val == "LOW":
                return "background-color: #d4edda"
            return ""
        
        st.dataframe(
            df_display.style.applymap(color_risk, subset=["Mức"] if "Mức" in df_display.columns else []),
            use_container_width=True,
            hide_index=True
        )
        
        st.write(f"Hiển thị **{len(predictions)}** bản ghi")
    else:
        st.info("Không có dữ liệu dự đoán")

# ============================================
# TAB 5: Matrix Report
# ============================================

with tab5:
    st.markdown("### 📊 Ma trận Quốc tịch × Mục đích")
    
    st.info("""
    Bảng tổng hợp số lượng người theo quốc tịch và mục đích:
    - **Lao động**: Người có giấy phép lao động
    - **Du lịch**: Nhập cảnh với mục đích du lịch
    - **Thăm thân**: Kết hôn, MĐK, thăm người thân
    - **Khác**: Các mục đích khác / chưa xác định
    """)
    
    # Get matrix report
    matrix_data = get_matrix_report(
        date_from=date_from_str,
        date_to=date_to_str,
        continent=continent,
        min_days=min_days_val
    )
    
    if matrix_data and matrix_data["matrix"]:
        import pandas as pd
        
        # Create DataFrame
        df_matrix = pd.DataFrame(matrix_data["matrix"])
        
        # Rename columns for display
        df_matrix.columns = ["Quốc tịch", "Tổng", "Lao động", "Du lịch", "Thăm thân", "Khác", "%"]
        
        # Display summary
        summary = matrix_data["summary"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tổng số người", f"{summary['total_records']:,}")
        with col2:
            st.metric("Số quốc tịch", summary['unique_nationalities'])
        
        # Display matrix table
        st.dataframe(
            df_matrix,
            use_container_width=True,
            hide_index=True
        )
        
        # Add totals row info
        totals = matrix_data["totals"]
        st.markdown(f"""
        **Tổng cộng**: {totals['tong']:,} người | 
        Lao động: {totals['lao_dong']:,} | 
        Du lịch: {totals['du_lich']:,} | 
        Thăm thân: {totals['tham_than']:,} | 
        Khác: {totals['khac']:,}
        """)
        
        # Chart
        import plotly.express as px
        
        # Top 10 for chart
        df_chart = df_matrix.head(10).melt(
            id_vars=["Quốc tịch"],
            value_vars=["Lao động", "Du lịch", "Thăm thân", "Khác"],
            var_name="Mục đích",
            value_name="Số người"
        )
        
        fig = px.bar(
            df_chart,
            x="Quốc tịch",
            y="Số người",
            color="Mục đích",
            title="Top 10 quốc tịch theo mục đích",
            barmode="stack"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("### 📊 Hướng dẫn")
    st.markdown("""
    1. Chọn **khoảng thời gian** để lọc
    2. Chọn **châu lục** hoặc **mục đích**
    3. Bấm **Áp dụng bộ lọc**
    4. Xem kết quả ở các tab
    5. **Xuất Excel** để lưu báo cáo
    
    ---
    
    ### 💡 Mẹo
    - Để xem tất cả: bỏ trống bộ lọc
    - Số ngày = 0: không lọc theo ngày
    - Export Excel: lấy toàn bộ dữ liệu
    """)
