"""
QLNNN Offline - Statistics Module
Port từ getStatistics(), getStatisticsPersonList(), generateNarrativeText()
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
import sys
from pathlib import Path
import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection, execute_query
from utils.date_utils import format_date_for_db, format_date_vn
from config import get_continent, CONTINENT_RULES, PAGE_SIZE
from utils.filter_utils import (
    build_continent_condition, 
    build_date_conditions, 
    build_residence_status_condition
)


@st.cache_data(ttl=3600)
def get_statistics(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    days_operator: str = ">=",
    days_value: int = None,
    residence_status: str = None,
    min_days: int = None
) -> Dict[str, Any]:
    """
    Get aggregated statistics based on filters
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)  
        continent: Filter by continent
        days_operator: Comparison operator for days (>= or <=)
        days_value: Number of days to compare
        residence_status: Filter by status (Lao động, Kết hôn, etc.)
        
    Returns:
        Dictionary with statistics
    """
    # Build WHERE conditions
    conditions = []
    params = []
    
    # Date filters
    date_conds, date_params = build_date_conditions(date_from, date_to, min_days)
    conditions.extend(date_conds)
    params.extend(date_params)
    
    # Continent filter
    cont_cond, cont_params = build_continent_condition(continent)
    if cont_cond:
        conditions.append(cont_cond)
        params.extend(cont_params)
    
    if days_value is not None:
        op = ">=" if days_operator == ">=" else "<="
        conditions.append(f"tong_ngay_luu_tru_2025 {op} ?")
        params.append(days_value)
    
    # Residence status filter
    status_cond, status_params = build_residence_status_condition(residence_status)
    if status_cond:
        conditions.append(status_cond)
        params.extend(status_params)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Get statistics
    sql = f"""
    SELECT
        COUNT(*) as total_persons,
        COUNT(DISTINCT quoc_tich) as total_nationalities,
        SUM(CASE WHEN trang_thai_cuoi_cung = 'Lao động' THEN 1 ELSE 0 END) as labor_count,
        SUM(CASE WHEN trang_thai_cuoi_cung = 'Kết hôn' THEN 1 ELSE 0 END) as marriage_count,
        SUM(CASE WHEN trang_thai_cuoi_cung = 'Học tập' THEN 1 ELSE 0 END) as student_count,
        SUM(CASE WHEN trang_thai_cuoi_cung = 'Đối tượng chú ý' THEN 1 ELSE 0 END) as watchlist_count,
        SUM(CASE WHEN ngay_di IS NULL THEN 1 ELSE 0 END) as currently_residing,
        AVG(tong_ngay_luu_tru_2025) as avg_days
    FROM view_tong_hop_final
    WHERE {where_clause}
    """
    
    result = execute_query(sql, tuple(params))
    
    if result:
        stats = result[0]
        return {
            "total_persons": stats["total_persons"] or 0,
            "total_nationalities": stats["total_nationalities"] or 0,
            "labor_count": stats["labor_count"] or 0,
            "marriage_count": stats["marriage_count"] or 0,
            "student_count": stats["student_count"] or 0,
            "watchlist_count": stats["watchlist_count"] or 0,
            "currently_residing": stats["currently_residing"] or 0,
            "avg_days": round(stats["avg_days"] or 0, 1)
        }
    
    return {
        "total_persons": 0,
        "total_nationalities": 0,
        "labor_count": 0,
        "marriage_count": 0,
        "student_count": 0,
        "watchlist_count": 0,
        "currently_residing": 0,
        "avg_days": 0
    }


@st.cache_data(ttl=3600)
def get_statistics_by_nationality(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    min_days: int = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get statistics grouped by nationality
    
    Args:
        date_from: Start date
        date_to: End date
        continent: Filter by continent
        limit: Max results
        
    Returns:
        List of nationality statistics
    """
    conditions = []
    params = []
    
    # Date filters
    date_conds, date_params = build_date_conditions(date_from, date_to, min_days)
    conditions.extend(date_conds)
    params.extend(date_params)
    
    # Continent filter
    cont_cond, cont_params = build_continent_condition(continent)
    if cont_cond:
        conditions.append(cont_cond)
        params.extend(cont_params)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
    SELECT
        quoc_tich,
        COUNT(*) as count,
        SUM(CASE WHEN ngay_di IS NULL THEN 1 ELSE 0 END) as still_here
    FROM view_tong_hop_final
    WHERE {where_clause}
    GROUP BY quoc_tich
    ORDER BY count DESC
    LIMIT ?
    """
    
    params.append(limit)
    
    return execute_query(sql, tuple(params))


def get_person_list(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    days_operator: str = ">=",
    days_value: int = None,
    residence_status: str = None,
    limit: int = PAGE_SIZE,
    offset: int = 0,
    min_days: int = None
) -> Dict[str, Any]:
    """
    Get detailed list of persons with pagination
    
    Args:
        Same as get_statistics plus limit/offset
        
    Returns:
        Dict with results and pagination info
    """
    conditions = []
    params = []
    
    # Date filters
    date_conds, date_params = build_date_conditions(date_from, date_to, min_days)
    conditions.extend(date_conds)
    params.extend(date_params)
    
    # Continent filter
    cont_cond, cont_params = build_continent_condition(continent)
    if cont_cond:
        conditions.append(cont_cond)
        params.extend(cont_params)
    
    if days_value is not None:
        op = ">=" if days_operator == ">=" else "<="
        conditions.append(f"tong_ngay_luu_tru_2025 {op} ?")
        params.append(days_value)
    
    # Residence status filter
    status_cond, status_params = build_residence_status_condition(residence_status)
    if status_cond:
        conditions.append(status_cond)
        params.extend(status_params)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Count total
    count_sql = f"""
    SELECT COUNT(*) as total
    FROM view_tong_hop_final
    WHERE {where_clause}
    """
    
    conn = get_connection()
    total_result = conn.execute(count_sql, tuple(params)).fetchone()
    total = total_result[0] if total_result else 0
    
    # Get results
    sql = f"""
    SELECT 
        ho_ten,
        ngay_sinh,
        quoc_tich,
        so_ho_chieu,
        ngay_den,
        ngay_di,
        dia_chi_tam_tru,
        so_lan_nhap_canh,
        tong_ngay_luu_tru_2025,
        tong_ngay_tich_luy,
        ket_qua_xac_minh,
        muc_dich_he_thong,
        trang_thai_cuoi_cung,
        labor_detail,
        marriage_detail,
        watchlist_detail
    FROM view_tong_hop_final
    WHERE {where_clause}
    ORDER BY ngay_den DESC
    LIMIT ? OFFSET ?
    """
    
    query_params = list(params) + [limit, offset]
    results = execute_query(sql, tuple(query_params))
    
    has_more = (offset + len(results)) < total
    
    return {
        "results": results,
        "total": total,
        "hasMore": has_more,
        "offset": offset,
        "limit": limit
    }


@st.cache_data(ttl=3600)
def generate_narrative(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    days_operator: str = ">=",
    days_value: int = None,
    residence_status: str = None,
    min_days: int = None
) -> str:
    """
    Generate narrative text for statistics (tường thuật)
    
    Args:
        Same filter parameters as get_statistics
        
    Returns:
        Formatted narrative text
    """
    stats = get_statistics(
        date_from, date_to, continent, 
        days_operator, days_value, residence_status, min_days
    )
    
    by_nationality = get_statistics_by_nationality(
        date_from, date_to, continent, min_days=min_days, limit=10
    )
    
    # Build narrative
    lines = []
    
    # Header
    period = ""
    if date_from and date_to:
        period = f"từ {format_date_vn(date_from)} đến {format_date_vn(date_to)}"
    elif date_from:
        period = f"từ {format_date_vn(date_from)}"
    elif date_to:
        period = f"đến {format_date_vn(date_to)}"
    
    if min_days:
        period_suffix = f" (Tổng ngày lưu trú >= {min_days} ngày)"
        period += period_suffix
    
    if period:
        lines.append(f"**Thời gian**: {period}")
    
    lines.append("")
    lines.append(f"**Tổng số người nước ngoài**: {stats['total_persons']:,} người")
    lines.append(f"- Đến từ {stats['total_nationalities']} quốc tịch khác nhau")
    lines.append(f"- Đang lưu trú: {stats['currently_residing']:,} người")
    lines.append(f"- Thời gian lưu trú trung bình: {stats['avg_days']} ngày")
    
    lines.append("")
    lines.append("**Phân loại theo mục đích**:")
    
    if stats['labor_count'] > 0:
        lines.append(f"- Lao động: {stats['labor_count']:,} người")
    if stats['marriage_count'] > 0:
        lines.append(f"- Kết hôn: {stats['marriage_count']:,} người")
    if stats['student_count'] > 0:
        lines.append(f"- Học tập: {stats['student_count']:,} người")
    if stats['watchlist_count'] > 0:
        lines.append(f"- ⚠️ Đối tượng chú ý: {stats['watchlist_count']:,} người")
    
    if by_nationality:
        lines.append("")
        lines.append("**Top quốc tịch**:")
        for i, nat in enumerate(by_nationality[:5], 1):
            lines.append(f"{i}. {nat['quoc_tich']}: {nat['count']:,} người (còn ở: {nat['still_here']})")
    
    return "\n".join(lines)


def get_last_update_time() -> str:
    """
    Get the last data update timestamp
    
    Returns:
        Formatted datetime string
    """
    sql = """
    SELECT MAX(thoi_diem_cap_nhat) as last_update
    FROM raw_immigration
    """
    
    result = execute_query(sql)
    
    if result and result[0]["last_update"]:
        last_update = result[0]["last_update"]
        if isinstance(last_update, str):
            return last_update
        return last_update.strftime("%d/%m/%Y %H:%M")
    
    return "Chưa có dữ liệu"


@st.cache_data(ttl=3600)
def get_ml_predictions(risk_level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Dự đoán mục đích dựa trên quy tắc (Rule-based ML Predictions)
    Port từ getMLPredictions() trong webapp.gs
    
    Quy tắc tính điểm rủi ro:
    - Địa chỉ: công ty/cty (+2), KCN/CCN (+3), homestay/resort (+1), Bảo Yên/KDC (+2)
    - Thời gian: >=90 ngày (+3), >=30 ngày (+2), >=8 ngày (+1)
    - Số lần nhập cảnh: >=5 lần (+2), >=3 lần (+1)
    - Mục đích: Lao động (+2), Kết hôn/Thăm thân (+1)
    
    Args:
        risk_level: Mức rủi ro (HIGH, MEDIUM, LOW) hoặc None để lấy tất cả
        limit: Số bản ghi tối đa
        
    Returns:
        Danh sách người với điểm rủi ro và lý do dự đoán
    """
    sql = """
    WITH prediction_data AS (
        SELECT 
            ho_ten,
            so_ho_chieu,
            quoc_tich,
            ngay_sinh,
            ngay_den,
            dia_chi_tam_tru,
            muc_dich_he_thong,
            trang_thai_cuoi_cung,
            tong_ngay_luu_tru_2025,
            so_lan_nhap_canh,
            
            -- Tính điểm rủi ro
            (
                -- Điểm địa chỉ (0-3)
                CASE 
                    WHEN LOWER(dia_chi_tam_tru) LIKE '%ccn%' OR LOWER(dia_chi_tam_tru) LIKE '%kcn%' 
                         OR LOWER(dia_chi_tam_tru) LIKE '%khu công nghiệp%' OR LOWER(dia_chi_tam_tru) LIKE '%cụm công nghiệp%' THEN 3
                    WHEN LOWER(dia_chi_tam_tru) LIKE '%công ty%' OR LOWER(dia_chi_tam_tru) LIKE '%cty%' THEN 2
                    WHEN LOWER(dia_chi_tam_tru) LIKE '%bảo yên%' OR LOWER(dia_chi_tam_tru) LIKE '%lô cc%' 
                         OR LOWER(dia_chi_tam_tru) LIKE '%kdc%' OR LOWER(dia_chi_tam_tru) LIKE '%đồng trung%'
                         OR LOWER(dia_chi_tam_tru) LIKE '%nà chiềng%' THEN 2
                    WHEN LOWER(dia_chi_tam_tru) LIKE '%homestay%' OR LOWER(dia_chi_tam_tru) LIKE '%resort%' THEN 1
                    ELSE 0
                END
                +
                -- Điểm thời gian tạm trú (0-3)
                CASE 
                    WHEN tong_ngay_luu_tru_2025 >= 90 THEN 3
                    WHEN tong_ngay_luu_tru_2025 >= 30 THEN 2
                    WHEN tong_ngay_luu_tru_2025 >= 8 THEN 1
                    ELSE 0
                END
                +
                -- Điểm số lần nhập cảnh (0-2)
                CASE 
                    WHEN so_lan_nhap_canh >= 5 THEN 2
                    WHEN so_lan_nhap_canh >= 3 THEN 1
                    ELSE 0
                END
                +
                -- Điểm mục đích (0-2)
                CASE 
                    WHEN LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%lao động%' THEN 2
                    WHEN LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%kết hôn%' 
                         OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%thăm thân%' THEN 1
                    ELSE 0
                END
            ) as risk_score
            
        FROM view_tong_hop_final
    )
    SELECT 
        *,
        CASE 
            WHEN risk_score >= 6 THEN 'HIGH'
            WHEN risk_score >= 3 THEN 'MEDIUM'
            ELSE 'LOW'
        END as risk_level_calc,
        
        -- Lý do dự đoán
        CASE 
            WHEN LOWER(dia_chi_tam_tru) LIKE '%ccn%' OR LOWER(dia_chi_tam_tru) LIKE '%kcn%' THEN 'Địa chỉ KCN/CCN'
            WHEN LOWER(dia_chi_tam_tru) LIKE '%công ty%' OR LOWER(dia_chi_tam_tru) LIKE '%cty%' THEN 'Địa chỉ công ty'
            ELSE NULL
        END as reason_address,
        
        CASE WHEN tong_ngay_luu_tru_2025 >= 30 THEN 'Tạm trú ' || CAST(tong_ngay_luu_tru_2025 AS VARCHAR) || ' ngày' ELSE NULL END as reason_days,
        CASE WHEN so_lan_nhap_canh >= 3 THEN 'Nhập cảnh ' || CAST(so_lan_nhap_canh AS VARCHAR) || ' lần' ELSE NULL END as reason_visits
        
    FROM prediction_data
    WHERE risk_score > 0
    ORDER BY risk_score DESC
    LIMIT ?
    """
    
    results = execute_query(sql, (limit,))
    
    # Filter by risk level if specified
    if risk_level:
        results = [r for r in results if r.get("risk_level_calc") == risk_level]
    
    # Build prediction reason string
    for r in results:
        reasons = []
        if r.get("reason_address"):
            reasons.append(r["reason_address"])
        if r.get("reason_days"):
            reasons.append(r["reason_days"])
        if r.get("reason_visits"):
            reasons.append(r["reason_visits"])
        r["prediction_reason"] = "; ".join(reasons) if reasons else "Nhiều yếu tố"
    
    return results


@st.cache_data(ttl=3600)
def generate_narrative_by_purpose(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    residence_status: str = None,
    min_days: int = None
) -> str:
    """
    Generate narrative text grouped by purpose (Lao động, Thăm thân, mđk)
    Port từ generateNarrativeText() trong webapp.gs
    
    Format output:
    Lao động: Trung Quốc: 05 người; Hàn Quốc: 03 người. Tổng số: 8 người.
    Thăm thân, mđk: Trung Quốc: 10 người; Đài Loan: 02 người. Tổng số: 12 người.
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        continent: Filter by continent
        residence_status: Filter by residence status
        
    Returns:
        Formatted narrative text
    """
    conditions = []
    params = []
    
    # Date filters
    # Note: generate_narrative_by_purpose logic slighty different, but let's see if we can adapt
    # It has specific logic for 'dang_tam_tru' vs 'da_ket_thuc' which build_date_conditions doesn't handle fully 
    # BUT build_residence_status_condition DOES handle it.
    
    # Re-implementing logic using helpers where consistent:
    
    # 1. Date filters (if not special status)
    if residence_status != 'dang_tam_tru':
        if date_from:
            conditions.append("ngay_den >= ?")
            params.append(date_from)
        if date_to and not min_days:
            conditions.append("ngay_den <= ?") # Note: Original was strict <=, our helper uses <= OR NULL. Keep original for safety?
            # Actually, let's keep it close to original for this specific function to avoid subtle bugs
            params.append(date_to)
    
    if min_days is not None:
        conditions.append("tong_ngay_luu_tru_2025 >= ?")
        params.append(min_days)

    # 2. Continent
    cont_cond, cont_params = build_continent_condition(continent)
    if cont_cond:
        conditions.append(cont_cond)
        params.extend(cont_params)
        
    # 3. Status special handling
    status_cond, status_params = build_residence_status_condition(residence_status)
    if status_cond:
        conditions.append(status_cond)
        params.extend(status_params)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Query to group by purpose and nationality
    sql = f"""
    WITH purpose_data AS (
        SELECT 
            CASE 
                WHEN LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%lao động%' THEN 'Lao động'
                WHEN LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%thăm thân%' 
                     OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%mđk%'
                     OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%kết hôn%' THEN 'Thăm thân, mđk'
                ELSE NULL
            END as muc_dich_group,
            quoc_tich,
            COUNT(*) as so_nguoi
        FROM view_tong_hop_final
        WHERE {where_clause}
            AND (
                LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%lao động%'
                OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%thăm thân%'
                OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%mđk%'
                OR LOWER(COALESCE(trang_thai_cuoi_cung, '')) LIKE '%kết hôn%'
            )
        GROUP BY muc_dich_group, quoc_tich
    )
    SELECT 
        muc_dich_group,
        quoc_tich,
        so_nguoi
    FROM purpose_data
    WHERE muc_dich_group IS NOT NULL
    ORDER BY muc_dich_group, so_nguoi DESC
    """
    
    results = execute_query(sql, tuple(params))
    
    # Group data by purpose
    purpose_groups = {}
    for row in results:
        purpose = row.get("muc_dich_group")
        nationality = row.get("quoc_tich")
        count = row.get("so_nguoi", 0)
        
        if purpose not in purpose_groups:
            purpose_groups[purpose] = []
        purpose_groups[purpose].append({"nationality": nationality, "count": count})
    
    # Format text
    narrative_lines = []
    purpose_order = ['Lao động', 'Thăm thân, mđk']
    
    for purpose in purpose_order:
        if purpose in purpose_groups and purpose_groups[purpose]:
            items = purpose_groups[purpose]
            total = sum(item["count"] for item in items)
            
            # Format: "Quốc tịch: số người" với số có leading zero nếu < 10
            details = []
            for item in items:
                count_str = f"0{item['count']}" if item["count"] < 10 else str(item["count"])
                details.append(f"{item['nationality']}: {count_str} người")
            
            narrative_lines.append(f"{purpose}: {'; '.join(details)}. Tổng số: {total} người.")
    
    return "\n\n".join(narrative_lines)


@st.cache_data(ttl=3600)
def get_matrix_report(
    date_from: str = None,
    date_to: str = None,
    continent: str = None,
    min_days: int = None
) -> Dict[str, Any]:
    """
    Tạo báo cáo Ma trận Quốc tịch × Mục đích (Dự đoán)
    Port từ getMatrixReport() trong webapp.gs
    
    Sử dụng logic DỰ ĐOÁN mục đích (prediction engine) dựa trên:
    - Địa chỉ: KCN/CCN, Công ty → Lao động
    - Số ngày lưu trú + số lần nhập cảnh → Lao động / Thăm thân
    - Mặc định nếu ngắn hạn → Du lịch
    
    Ma trận pivot:
    | Quốc tịch | Tổng | Lao động | Du lịch | Thăm thân | Khác | % |
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        continent: Filter by continent
        
    Returns:
        Dict with matrix, summary, and totals
    """
    conditions = []
    params = []
    
    # Date filters
    date_conds, date_params = build_date_conditions(date_from, date_to, min_days)
    # Note: get_matrix_report uses STRICT date_to ("ngay_den <= ?") in original, 
    # whereas build_date_conditions uses range check on end_date. 
    # Let's keep original logic for date_to to match "Arrival Date" semantics usually desired in Matrix
    
    if date_from:
        conditions.append("ngay_den >= ?")
        params.append(date_from)
    
    if date_to and not min_days:
        conditions.append("ngay_den <= ?")
        params.append(date_to)

    if min_days is not None:
        conditions.append("tong_ngay_luu_tru_2025 >= ?")
        params.append(min_days)
        
    # Continent filter
    cont_cond, cont_params = build_continent_condition(continent)
    if cont_cond:
        conditions.append(cont_cond)
        params.extend(cont_params)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Query: Dự đoán mục đích dựa trên quy tắc (giống prediction engine của GAS)
    # Cần tính tuổi và xác định nhóm có trẻ em hay không
    sql = f"""
    WITH pre_processed AS (
        SELECT *,
            -- Tính tuổi (ước lượng theo năm)
            DATE_DIFF('year', ngay_sinh, CURRENT_DATE) as tuoi,
            
            -- Đánh dấu nếu trong nhóm (cùng ngày đến, cùng địa chỉ) có người dưới 18 tuổi
            MAX(CASE WHEN DATE_DIFF('year', ngay_sinh, CURRENT_DATE) < 18 THEN 1 ELSE 0 END) 
                OVER (PARTITION BY ngay_den, dia_chi_tam_tru) as has_child_in_group
        FROM view_tong_hop_final
        WHERE {where_clause}
    ),
    prediction_engine AS (
        SELECT 
            UPPER(TRIM(COALESCE(quoc_tich, 'Không rõ'))) as quoc_tich,
            
            -- Dự đoán mục đích dựa trên quy tắc
            CASE
                -- 1. Ưu tiên: Đã có kết quả xác minh từ con người
                WHEN NULLIF(TRIM(ket_qua_xac_minh), '') IS NOT NULL 
                    THEN ket_qua_xac_minh
                    
                -- 2. Đã có mục đích từ hệ thống tham chiếu
                WHEN trang_thai_cuoi_cung IS NOT NULL AND trang_thai_cuoi_cung != ''
                    THEN trang_thai_cuoi_cung
                
                -- 3. Dự đoán Thăm thân (Nhóm có trẻ em)
                -- Rule: Bản thân < 18 tuổi HOẶC đi cùng nhóm với người < 18 tuổi
                WHEN has_child_in_group = 1
                    THEN 'Thăm thân (dự đoán)'
                    
                -- 4. Dự đoán theo địa chỉ
                -- Nhóm Lao động: KCN, Cty, KDC, Bảo Yên...
                WHEN LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%kcn%' 
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%ccn%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%công ty%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%cty%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%khu công nghiệp%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%bảo yên%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%lô cc%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%kdc%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%đồng trung%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%nà chiềng%'
                    THEN 'Lao động (dự đoán)'
                
                -- Nhóm Du lịch: Homestay, Resort -> Khác (theo yêu cầu tạm thời chưa tính Du lịch)
                WHEN LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%homestay%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%resort%'
                     OR LOWER(COALESCE(dia_chi_tam_tru, '')) LIKE '%khách sạn%'
                    THEN 'Khác'
                
                -- 5. Dự đoán theo thời gian & tần suất
                -- Rule: >= 3 ngày -> Lao động (buôn bán, làm việc thường xuyên)
                WHEN tong_ngay_luu_tru_2025 >= 3
                    THEN 'Lao động (dự đoán)'
                
                -- Rule: < 3 ngày và nhập cảnh 1 lần -> Khác
                WHEN tong_ngay_luu_tru_2025 < 3 AND so_lan_nhap_canh <= 1
                    THEN 'Khác'

                -- Mặc định còn lại -> Khác
                ELSE 'Khác'
            END as du_doan_final
            
        FROM pre_processed
    ),
    aggregated AS (
        SELECT 
            quoc_tich,
            COUNT(*) as tong,
            SUM(CASE WHEN LOWER(du_doan_final) LIKE '%lao động%' THEN 1 ELSE 0 END) as lao_dong,
            0 as du_lich, -- Tạm thời không tính Du lịch
            SUM(CASE WHEN LOWER(du_doan_final) LIKE '%thăm thân%' 
                      OR LOWER(du_doan_final) LIKE '%mđk%' 
                      OR LOWER(du_doan_final) LIKE '%kết hôn%' THEN 1 ELSE 0 END) as tham_than,
            SUM(CASE WHEN 
                LOWER(du_doan_final) NOT LIKE '%lao động%' 
                AND LOWER(du_doan_final) NOT LIKE '%thăm thân%'
                AND LOWER(du_doan_final) NOT LIKE '%mđk%'
                AND LOWER(du_doan_final) NOT LIKE '%kết hôn%'
            THEN 1 ELSE 0 END) as khac
        FROM prediction_engine
        GROUP BY quoc_tich
    ),
    grand_total AS (
        SELECT SUM(tong) as total FROM aggregated
    )
    SELECT 
        a.quoc_tich,
        a.tong,
        a.lao_dong,
        a.du_lich,
        a.tham_than,
        a.khac,
        ROUND(a.tong * 100.0 / NULLIF(g.total, 0), 2) as phan_tram
    FROM aggregated a
    CROSS JOIN grand_total g
    ORDER BY a.tong DESC
    LIMIT 50
    """
    
    results = execute_query(sql, tuple(params))
    
    # Parse matrix results
    matrix = []
    totals = {
        "tong": 0,
        "lao_dong": 0,
        "du_lich": 0,
        "tham_than": 0,
        "khac": 0
    }
    
    for row in results:
        item = {
            "quoc_tich": row.get("quoc_tich", "Không rõ"),
            "tong": row.get("tong", 0),
            "lao_dong": row.get("lao_dong", 0),
            "du_lich": row.get("du_lich", 0),
            "tham_than": row.get("tham_than", 0),
            "khac": row.get("khac", 0),
            "phan_tram": row.get("phan_tram", 0)
        }
        matrix.append(item)
        
        # Accumulate totals
        totals["tong"] += item["tong"]
        totals["lao_dong"] += item["lao_dong"]
        totals["du_lich"] += item["du_lich"]
        totals["tham_than"] += item["tham_than"]
        totals["khac"] += item["khac"]
    
    # Get summary stats
    summary = {
        "total_records": totals["tong"],
        "unique_nationalities": len(matrix),
        "date_from": date_from,
        "date_to": date_to
    }
    
    return {
        "matrix": matrix,
        "totals": totals,
        "summary": summary
    }

