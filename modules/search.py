"""
QLNNN Offline - Search Module
Port từ searchPassport() và searchBatchPassports() trong webapp.gs
"""

from typing import List, Dict, Any, Optional
from functools import lru_cache
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection, execute_query
from utils.text_utils import normalize_passport, normalize_for_search, split_passports
from config import PAGE_SIZE, MAX_BATCH_SIZE


def search_single(keyword: str) -> List[Dict[str, Any]]:
    """
    Search for a single passport or name
    Feature: Fuzzy search ignoring spaces and case
    Example: 'hewu' matches 'He Wuyang', 'E 123' matches 'E123456'
    
    Args:
        keyword: Passport number or name to search
        
    Returns:
        List of matching records
    """
    if not keyword or len(keyword.strip()) < 2:
        return []
    
    # Pre-process keyword: remove diacritics, upper, remove spaces
    from utils.text_utils import remove_diacritics
    
    raw_keyword = keyword.strip()
    # Normalize for comparison: NO spaces, uppercase, no diacritics
    clean_keyword = remove_diacritics(raw_keyword).upper().replace(" ", "")
    
    # Build query - search in the aggregated view using REPLACE to ignore spaces in DB
    sql = """
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
    WHERE 
        -- Search Passport: ignore spaces
        REPLACE(UPPER(so_ho_chieu), ' ', '') LIKE ? 
        
        -- Search Name: ignore spaces (support fuzzy name search)
        OR REPLACE(UPPER(ho_ten), ' ', '') LIKE ?
        
        -- Fallback: Original keyword fuzzy search (just in case)
        OR UPPER(ho_ten) LIKE ?
    ORDER BY ngay_den DESC
    LIMIT 100
    """
    
    # Search patterns
    # 1. Exact/Substring match on normalized data
    # e.g. Data: "He Wuyang" -> "HEWUYANG". Keyword: "hewu" -> Match
    pattern_normalized = f"%{clean_keyword}%"
    
    # 2. Original pattern (for safety, though normalized usually covers it)
    pattern_original = f"%{raw_keyword.upper()}%"
    
    return execute_query(sql, (pattern_normalized, pattern_normalized, pattern_original))


def search_batch(keywords: List[str], limit: int = PAGE_SIZE, 
                 offset: int = 0) -> Dict[str, Any]:
    """
    Search for multiple passports (batch search)
    
    Args:
        keywords: List of passport numbers
        limit: Results per page
        offset: Pagination offset
        
    Returns:
        Dict with results and pagination info
    """
    if not keywords:
        return {"results": [], "total": 0, "hasMore": False}
    
    # Normalize and deduplicate
    normalized = list(set([normalize_passport(k) for k in keywords if k]))
    
    if not normalized:
        return {"results": [], "total": 0, "hasMore": False}
    
    # Limit batch size
    if len(normalized) > MAX_BATCH_SIZE:
        normalized = normalized[:MAX_BATCH_SIZE]
    
    # Build IN clause
    placeholders = ", ".join(["?" for _ in normalized])
    
    # Count total
    count_sql = f"""
    SELECT COUNT(*) as total
    FROM view_tong_hop_final
    WHERE UPPER(so_ho_chieu) IN ({placeholders})
    """
    
    conn = get_connection()
    total_result = conn.execute(count_sql, normalized).fetchone()
    total = total_result[0] if total_result else 0
    
    # Get paginated results
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
    WHERE UPPER(so_ho_chieu) IN ({placeholders})
    ORDER BY 
        CASE 
            WHEN trang_thai_cuoi_cung = 'Đối tượng chú ý' THEN 1
            WHEN trang_thai_cuoi_cung = 'Lao động' THEN 2
            WHEN trang_thai_cuoi_cung = 'Kết hôn' THEN 3
            WHEN trang_thai_cuoi_cung = 'Học tập' THEN 4
            ELSE 5
        END,
        ngay_den DESC
    LIMIT ? OFFSET ?
    """
    
    params = normalized + [limit, offset]
    results = execute_query(sql, tuple(params))
    
    has_more = (offset + len(results)) < total
    
    return {
        "results": results,
        "total": total,
        "hasMore": has_more,
        "offset": offset,
        "limit": limit
    }


def search_batch_all(keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Get all batch search results (for export)
    
    Args:
        keywords: List of passport numbers
        
    Returns:
        All matching records
    """
    if not keywords:
        return []
    
    normalized = list(set([normalize_passport(k) for k in keywords if k]))
    
    if not normalized:
        return []
    
    if len(normalized) > MAX_BATCH_SIZE:
        normalized = normalized[:MAX_BATCH_SIZE]
    
    placeholders = ", ".join(["?" for _ in normalized])
    
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
    WHERE UPPER(so_ho_chieu) IN ({placeholders})
    ORDER BY 
        CASE 
            WHEN trang_thai_cuoi_cung = 'Đối tượng chú ý' THEN 1
            WHEN trang_thai_cuoi_cung = 'Lao động' THEN 2
            WHEN trang_thai_cuoi_cung = 'Kết hôn' THEN 3
            WHEN trang_thai_cuoi_cung = 'Học tập' THEN 4
            ELSE 5
        END,
        ngay_den DESC
    """
    
    return execute_query(sql, tuple(normalized))


def get_not_found(keywords: List[str], found_passports: List[str]) -> List[str]:
    """
    Get list of passports that were not found in search
    
    Args:
        keywords: Original search keywords
        found_passports: Passports that were found
        
    Returns:
        List of not found passports
    """
    normalized_keywords = set([normalize_passport(k) for k in keywords if k])
    normalized_found = set([normalize_passport(p) for p in found_passports])
    
    return list(normalized_keywords - normalized_found)
