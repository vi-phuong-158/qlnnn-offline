"""
QLNNN Offline - Search Module
Port từ searchPassport() và searchBatchPassports() trong webapp.gs

Optimized Version:
- Extracted SEARCH_COLUMNS constant (DRY)
- Eliminated redundant COUNT query via window function
- Pre-normalize keywords in Python for better index utilization
"""

from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_connection, execute_query
from utils.text_utils import (
    normalize_passport, 
    normalize_for_search, 
    split_passports,
    remove_diacritics
)
from config import PAGE_SIZE, MAX_BATCH_SIZE


# ============================================
# CONSTANTS
# ============================================

# Column list for search results - extracted for DRY principle
SEARCH_COLUMNS = """
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
"""

# Status priority order for sorting
STATUS_PRIORITY_CASE = """
    CASE 
        WHEN trang_thai_cuoi_cung = 'Đối tượng chú ý' THEN 1
        WHEN trang_thai_cuoi_cung = 'Lao động' THEN 2
        WHEN trang_thai_cuoi_cung = 'Kết hôn' THEN 3
        WHEN trang_thai_cuoi_cung = 'Học tập' THEN 4
        ELSE 5
    END
"""


# ============================================
# SINGLE SEARCH
# ============================================

def search_single(keyword: str) -> List[Dict[str, Any]]:
    """
    Search for a single passport or name.
    
    Features:
    - Fuzzy search ignoring spaces and case
    - Example: 'hewu' matches 'He Wuyang', 'E 123' matches 'E123456'
    
    Args:
        keyword: Passport number or name to search
        
    Returns:
        List of matching records
    """
    if not keyword or len(keyword.strip()) < 2:
        return []
    
    raw_keyword = keyword.strip()
    
    # Pre-normalize keyword in Python (faster than SQL functions on every row)
    # Normalize: UPPER, remove spaces, remove diacritics
    clean_keyword = remove_diacritics(raw_keyword).upper().replace(" ", "")
    
    # Build optimized query
    # The view already has so_ho_chieu as TRIM(UPPER(...)), so we can match directly
    sql = f"""
    SELECT {SEARCH_COLUMNS}
    FROM view_tong_hop_final
    WHERE 
        -- Passport search: view already has normalized so_ho_chieu (TRIM UPPER)
        -- We still need REPLACE for space-insensitive matching
        REPLACE(so_ho_chieu, ' ', '') LIKE ? 
        
        -- Name search: ignore spaces for fuzzy matching
        OR REPLACE(UPPER(ho_ten), ' ', '') LIKE ?
        
        -- Fallback: Original keyword for exact match
        OR UPPER(ho_ten) LIKE ?
    ORDER BY ngay_den DESC
    LIMIT 100
    """
    
    # Search patterns
    pattern_normalized = f"%{clean_keyword}%"
    pattern_original = f"%{raw_keyword.upper()}%"
    
    return execute_query(sql, (pattern_normalized, pattern_normalized, pattern_original))


# ============================================
# BATCH SEARCH
# ============================================

def search_batch(
    keywords: List[str], 
    limit: int = PAGE_SIZE, 
    offset: int = 0
) -> Dict[str, Any]:
    """
    Search for multiple passports (batch search).
    
    Optimized: Uses window function COUNT(*) OVER() to avoid separate COUNT query.
    
    Args:
        keywords: List of passport numbers
        limit: Results per page
        offset: Pagination offset
        
    Returns:
        Dict with results and pagination info
    """
    if not keywords:
        return {"results": [], "total": 0, "hasMore": False}
    
    # Pre-normalize keywords in Python (move work to app layer)
    normalized = _deduplicate_and_normalize(keywords)
    
    if not normalized:
        return {"results": [], "total": 0, "hasMore": False}
    
    # Limit batch size
    if len(normalized) > MAX_BATCH_SIZE:
        normalized = normalized[:MAX_BATCH_SIZE]
    
    # Build parameterized IN clause
    placeholders = ", ".join(["?" for _ in normalized])
    
    # OPTIMIZED: Single query with window function for total count
    # This eliminates the need for a separate COUNT(*) query
    sql = f"""
    SELECT 
        {SEARCH_COLUMNS},
        COUNT(*) OVER() as _total_count
    FROM view_tong_hop_final
    WHERE so_ho_chieu IN ({placeholders})
    ORDER BY {STATUS_PRIORITY_CASE}, ngay_den DESC
    LIMIT ? OFFSET ?
    """
    
    params = tuple(normalized) + (limit, offset)
    
    conn = get_connection()
    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    
    if not rows:
        return {
            "results": [],
            "total": 0,
            "hasMore": False,
            "offset": offset,
            "limit": limit
        }
    
    # Extract total from first row's _total_count column
    total_idx = columns.index("_total_count")
    total = rows[0][total_idx]
    
    # Convert to dicts, excluding the _total_count column
    result_columns = [c for c in columns if c != "_total_count"]
    results = []
    for row in rows:
        record = {}
        for i, col in enumerate(columns):
            if col != "_total_count":
                record[col] = row[i]
        results.append(record)
    
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
    Get all batch search results (for export).
    
    Args:
        keywords: List of passport numbers
        
    Returns:
        All matching records
    """
    if not keywords:
        return []
    
    normalized = _deduplicate_and_normalize(keywords)
    
    if not normalized:
        return []
    
    if len(normalized) > MAX_BATCH_SIZE:
        normalized = normalized[:MAX_BATCH_SIZE]
    
    placeholders = ", ".join(["?" for _ in normalized])
    
    sql = f"""
    SELECT {SEARCH_COLUMNS}
    FROM view_tong_hop_final
    WHERE so_ho_chieu IN ({placeholders})
    ORDER BY {STATUS_PRIORITY_CASE}, ngay_den DESC
    """
    
    return execute_query(sql, tuple(normalized))


# ============================================
# HELPER FUNCTIONS
# ============================================

def _deduplicate_and_normalize(keywords: List[str]) -> List[str]:
    """
    Normalize and deduplicate a list of passport keywords.
    
    Args:
        keywords: Raw keyword list
        
    Returns:
        Deduplicated, normalized list
    """
    seen = set()
    result = []
    for k in keywords:
        if k:
            normalized = normalize_passport(k)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
    return result


def get_not_found(keywords: List[str], found_passports: List[str]) -> List[str]:
    """
    Get list of passports that were not found in search.
    
    Args:
        keywords: Original search keywords
        found_passports: Passports that were found
        
    Returns:
        List of not found passports
    """
    normalized_keywords = set(_deduplicate_and_normalize(keywords))
    normalized_found = set(_deduplicate_and_normalize(found_passports))
    
    return list(normalized_keywords - normalized_found)
