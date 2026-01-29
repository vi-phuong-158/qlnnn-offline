"""
QLNNN Offline - Cấu hình hệ thống
Centralized configuration (port từ Config.gs)
"""

import os
from pathlib import Path

# ============================================
# PATHS
# ============================================

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
IMPORTS_DIR = DATA_DIR / "imports"

# Database
DATABASE_PATH = DATA_DIR / "qlnnn.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
IMPORTS_DIR.mkdir(exist_ok=True)

# ============================================
# DATABASE SETTINGS
# ============================================

DB_CONFIG = {
    "path": str(DATABASE_PATH),
    "read_only": False,
}

# ============================================
# USER ROLES & PERMISSIONS
# ============================================

# Default admin user (password will be hashed)
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",  # Change this on first login!
    "role": "admin",
    "full_name": "Administrator"
}

ROLE_ADMIN = "admin"
ROLE_COMMUNE = "commune"

# Permissions by role
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "search",
        "batch_search",
        "statistics",
        "import_data",
        "export_data",
        "manage_users",
        "manage_refs",
        "ml_predictions"
    ],
    ROLE_COMMUNE: [
        "search",
        "batch_search",
        "export_data",
        "update_verification"
    ]
}

# ============================================
# RATE LIMITING
# ============================================

RATE_LIMITS = {
    "admin": {
        "requests_per_minute": 120,
        "batch_size": 2000
    },
    "commune": {
        "requests_per_minute": 60,
        "batch_size": 1000
    }
}

# ============================================
# SESSION SETTINGS
# ============================================

SESSION_TTL_HOURS = 12
PASSWORD_MIN_LENGTH = 6

# ============================================
# CONTINENT MAPPING
# ============================================

CONTINENT_RULES = {
    "ASIA": [
        "CHN", "CHINA", "TRUNG QUỐC", "JPN", "JAPAN", "NHẬT BẢN", "KOR", "KOREA", "HÀN QUỐC",
        "THA", "THAILAND", "THÁI LAN", "VNM", "VIETNAM", "VIỆT NAM", "MYS", "MALAYSIA",
        "SGP", "SINGAPORE", "IDN", "INDONESIA", "PHL", "PHILIPPINES", "IND", "INDIA", "ẤN ĐỘ",
        "TWN", "TAIWAN", "ĐÀI LOAN", "HKG", "HONG KONG", "MAC", "MACAU", "LAO", "LAOS", "LÀO",
        "KHM", "CAMBODIA", "CAMPUCHIA", "MMR", "MYANMAR", "BGD", "BANGLADESH", "PAK", "PAKISTAN",
        "NPL", "NEPAL", "LKA", "SRI LANKA", "MNG", "MONGOLIA", "MÔNG CỔ"
    ],
    "EUROPE": [
        "GBR", "UK", "ANH", "FRA", "FRANCE", "PHÁP", "DEU", "GERMANY", "ĐỨC",
        "ITA", "ITALY", "Ý", "ESP", "SPAIN", "TÂY BAN NHA", "NLD", "NETHERLANDS", "HÀ LAN",
        "BEL", "BELGIUM", "BỈ", "CHE", "SWITZERLAND", "THỤY SĨ", "AUT", "AUSTRIA", "ÁO",
        "SWE", "SWEDEN", "THỤY ĐIỂN", "NOR", "NORWAY", "NA UY", "DNK", "DENMARK", "ĐAN MẠCH",
        "FIN", "FINLAND", "PHẦN LAN", "POL", "POLAND", "BA LAN", "CZE", "CZECH", "SÉC",
        "RUS", "RUSSIA", "NGA", "UKR", "UKRAINE", "PRT", "PORTUGAL", "BỒ ĐÀO NHA",
        "GRC", "GREECE", "HY LẠP", "IRL", "IRELAND", "AI LEN"
    ],
    "AMERICA": [
        "USA", "US", "MỸ", "HOA KỲ", "CAN", "CANADA", "MEX", "MEXICO",
        "BRA", "BRAZIL", "ARG", "ARGENTINA", "CHL", "CHILE", "COL", "COLOMBIA",
        "PER", "PERU", "VEN", "VENEZUELA", "ECU", "ECUADOR", "CUB", "CUBA"
    ],
    "OCEANIA": [
        "AUS", "AUSTRALIA", "ÚC", "NZL", "NEW ZEALAND", "TÂN TÂY LAN",
        "FJI", "FIJI", "PNG", "PAPUA NEW GUINEA"
    ],
    "AFRICA": [
        "ZAF", "SOUTH AFRICA", "NAM PHI", "EGY", "EGYPT", "AI CẬP",
        "NGA", "NIGERIA", "KEN", "KENYA", "MAR", "MOROCCO", "MA RỐC",
        "TUN", "TUNISIA", "GHA", "GHANA", "ETH", "ETHIOPIA"
    ]
}

# ============================================
# HEADER MAPPING (for Excel imports)
# ============================================

HEADER_MAP = {
    # Standard columns
    "stt": "stt",
    "ho_ten": "ho_ten",
    "ho_va_ten": "ho_ten",
    "ngay_sinh": "ngay_sinh",
    "ngaysinh": "ngay_sinh",
    "quoc_tich": "quoc_tich",
    "quoctich": "quoc_tich",
    "so_ho_chieu": "so_ho_chieu",
    "passport": "so_ho_chieu",
    "sohochieu": "so_ho_chieu",
    "ngay_den": "ngay_den",
    "ngayden": "ngay_den",
    "ngay_di": "ngay_di",
    "ngaydi": "ngay_di",
    "dia_chi": "dia_chi",
    "dia_chi_tam_tru": "dia_chi",
    "diachi": "dia_chi",
    "address": "dia_chi",
    
    # Verification result column
    "ket_qua_xac_minh": "ket_qua_xac_minh",
    "ketquaxacminh": "ket_qua_xac_minh",
    "xac_minh": "ket_qua_xac_minh",
    "ket_qua": "ket_qua_xac_minh",
    "verification_result": "ket_qua_xac_minh"
}

# ============================================
# UI SETTINGS
# ============================================

PAGE_SIZE = 200  # Results per page
MAX_BATCH_SIZE = 1000  # Max passports in batch search

# Color coding for result cards
STATUS_COLORS = {
    "Đối tượng chú ý": "#dc3545",  # Red
    "Lao động": "#ffc107",          # Yellow
    "Kết hôn": "#28a745",           # Green
    "Học tập": "#17a2b8",           # Blue
    "default": "#6c757d"            # Gray
}


def get_continent(nationality: str) -> str:
    """
    Get continent from nationality string
    
    Args:
        nationality: Nationality code or name
        
    Returns:
        Continent name or 'OTHER'
    """
    if not nationality:
        return "OTHER"
    
    nat_upper = nationality.upper().strip()
    
    for continent, countries in CONTINENT_RULES.items():
        if nat_upper in countries:
            return continent
    
    return "OTHER"
