"""
QLNNN Offline - Filter Utilities
DRY helpers for building SQL filter conditions
"""

from typing import Tuple, List, Union
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONTINENT_RULES


def build_continent_condition(
    continent: Union[str, List[str], None]
) -> Tuple[str, List[str]]:
    """
    Build SQL condition for continent/nationality filter.
    
    Args:
        continent: Single continent code, list of codes, or None/ALL
        
    Returns:
        Tuple of (sql_clause, params_list)
        Empty tuple if no filter needed
        
    Example:
        >>> clause, params = build_continent_condition("ASIA")
        >>> # clause = "UPPER(quoc_tich) IN (?, ?, ...)"
        >>> # params = ["CHN", "CHINA", "TRUNG QUỐC", ...]
    """
    if not continent:
        return "", []
    
    # Normalize to list
    if isinstance(continent, str):
        if continent == "ALL":
            return "", []
        continents_list = [continent]
    else:
        if "ALL" in continent:
            return "", []
        continents_list = continent
    
    # Collect countries from each continent
    countries = set()
    for c in continents_list:
        if c == "ASIA_OCEANIA":
            countries.update(CONTINENT_RULES.get("ASIA", []))
            countries.update(CONTINENT_RULES.get("OCEANIA", []))
        else:
            countries.update(CONTINENT_RULES.get(c, []))
    
    if not countries:
        return "", []
    
    countries_list = list(countries)
    placeholders = ", ".join(["?" for _ in countries_list])
    
    return f"UPPER(quoc_tich) IN ({placeholders})", countries_list


def build_date_conditions(
    date_from: str = None,
    date_to: str = None,
    min_days: int = None
) -> Tuple[str, List]:
    """
    Build SQL conditions for date range filters.
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        min_days: Minimum accumulated days filter
        
    Returns:
        Tuple of (list of SQL clauses, list of params)
    """
    conditions = []
    params = []
    
    if date_from:
        conditions.append("ngay_den >= ?")
        params.append(date_from)
    
    if date_to and not min_days:
        conditions.append("(ngay_di IS NULL OR ngay_di <= ?)")
        params.append(date_to)
    
    if min_days is not None:
        conditions.append("tong_ngay_luu_tru_2025 >= ?")
        params.append(min_days)
        # Also filter only those currently residing (not departed yet)
        conditions.append("(ngay_di IS NULL OR ngay_di >= CURRENT_DATE)")
    
    return conditions, params


def build_residence_status_condition(status: str) -> Tuple[str, List]:
    """
    Build SQL condition for residence status filter.
    
    Args:
        status: 'dang_tam_tru', 'da_ket_thuc', or specific status name
        
    Returns:
        Tuple of (sql_clause, params_list)
    """
    if not status:
        return "", []
    
    if status == 'dang_tam_tru':
        return "(ngay_di IS NULL OR ngay_di > CURRENT_DATE)", []
    elif status == 'da_ket_thuc':
        return "(ngay_di IS NOT NULL AND ngay_di <= CURRENT_DATE)", []
    else:
        return "trang_thai_cuoi_cung = ?", [status]
