"""
QLNNN Offline - Database Models & Schema
Create tables and initialize database
"""

from .connection import get_connection, table_exists
import bcrypt


# ============================================
# SCHEMA DEFINITIONS
# ============================================

SCHEMA_SQL = """
-- ============================================
-- USERS TABLE (Authentication)
-- ============================================
CREATE SEQUENCE IF NOT EXISTS seq_users_id;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_users_id'),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'commune',
    full_name TEXT,
    email TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- ============================================
-- MAIN DATA: raw_immigration
-- ============================================
CREATE SEQUENCE IF NOT EXISTS seq_raw_immigration_id;
CREATE TABLE IF NOT EXISTS raw_immigration (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_raw_immigration_id'),
    so_ho_chieu TEXT NOT NULL,
    ho_ten TEXT,
    ngay_sinh DATE,
    quoc_tich TEXT,
    ngay_den DATE,
    ngay_di DATE,
    dia_chi_tam_tru TEXT,
    ket_qua_xac_minh TEXT,
    thoi_diem_cap_nhat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file TEXT
);

-- Indexes for faster search
CREATE INDEX IF NOT EXISTS idx_passport ON raw_immigration(so_ho_chieu);
CREATE INDEX IF NOT EXISTS idx_ngay_den ON raw_immigration(ngay_den);
CREATE INDEX IF NOT EXISTS idx_quoc_tich ON raw_immigration(quoc_tich);
CREATE INDEX IF NOT EXISTS idx_ho_ten ON raw_immigration(ho_ten);
CREATE INDEX IF NOT EXISTS idx_last_update ON raw_immigration(thoi_diem_cap_nhat);

-- Composite indexes for batch search optimization
CREATE INDEX IF NOT EXISTS idx_passport_status ON raw_immigration(so_ho_chieu, ket_qua_xac_minh);
CREATE INDEX IF NOT EXISTS idx_passport_ngay_den ON raw_immigration(so_ho_chieu, ngay_den DESC);

-- ============================================
-- REFERENCE TABLES
-- ============================================

-- Lao động (Labor/Work Permit)
CREATE SEQUENCE IF NOT EXISTS seq_ref_labor_id;
CREATE TABLE IF NOT EXISTS ref_labor (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_ref_labor_id'),
    so_ho_chieu TEXT UNIQUE,
    vi_tri TEXT,
    noi_lam_viec TEXT,
    ngay_cap DATE
);

-- Du học sinh (Students)
CREATE SEQUENCE IF NOT EXISTS seq_ref_student_id;
CREATE TABLE IF NOT EXISTS ref_student (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_ref_student_id'),
    so_ho_chieu TEXT UNIQUE,
    truong TEXT,
    nganh TEXT
);

-- Đối tượng chú ý (Watchlist)
CREATE SEQUENCE IF NOT EXISTS seq_ref_watchlist_id;
CREATE TABLE IF NOT EXISTS ref_watchlist (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_ref_watchlist_id'),
    so_ho_chieu TEXT UNIQUE,
    dien TEXT,
    so_cong_van TEXT,
    ngay_nhap DATE
);

-- Kết hôn (Marriage)
CREATE SEQUENCE IF NOT EXISTS seq_ref_marriage_id;
CREATE TABLE IF NOT EXISTS ref_marriage (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_ref_marriage_id'),
    so_ho_chieu TEXT UNIQUE,
    ho_ten_vn TEXT,
    dia_chi TEXT,
    dien TEXT
);

-- Indexes for reference tables
CREATE INDEX IF NOT EXISTS idx_labor_passport ON ref_labor(so_ho_chieu);
CREATE INDEX IF NOT EXISTS idx_student_passport ON ref_student(so_ho_chieu);
CREATE INDEX IF NOT EXISTS idx_watchlist_passport ON ref_watchlist(so_ho_chieu);
CREATE INDEX IF NOT EXISTS idx_marriage_passport ON ref_marriage(so_ho_chieu);

-- ============================================
-- AUDIT LOG
-- ============================================
CREATE SEQUENCE IF NOT EXISTS seq_audit_log_id;
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY DEFAULT nextval('seq_audit_log_id'),
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# ============================================
# VIEW DEFINITION (port từ view_final.sql)
# ============================================

VIEW_SQL = """
CREATE OR REPLACE VIEW view_tong_hop_final AS
WITH
-- 1) Lọc trùng trong cùng (passport, ngay_den): lấy bản cập nhật mới nhất
UniqueEntries AS (
  SELECT * EXCLUDE(rn)
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER(
        PARTITION BY TRIM(UPPER(so_ho_chieu)), ngay_den
        ORDER BY
          thoi_diem_cap_nhat DESC,
          CASE WHEN ngay_di IS NULL THEN 1 ELSE 0 END,
          ngay_di DESC
      ) AS rn
    FROM raw_immigration
    WHERE so_ho_chieu IS NOT NULL AND so_ho_chieu != ''
  )
  WHERE rn = 1
),

BaseData AS (
  SELECT
    TRIM(UPPER(so_ho_chieu)) AS passport,
    ho_ten,
    ngay_sinh,
    quoc_tich,
    ngay_den,
    ngay_di,
    dia_chi_tam_tru,
    thoi_diem_cap_nhat,
    COALESCE(ngay_di, CURRENT_DATE) AS end_eff,
    ket_qua_xac_minh
  FROM UniqueEntries
),

-- 2) Lấy thông tin nhân thân mới nhất
PersonLatest AS (
  SELECT * EXCLUDE(rn)
  FROM (
    SELECT
      passport,
      ho_ten,
      ngay_sinh,
      quoc_tich,
      thoi_diem_cap_nhat,
      ROW_NUMBER() OVER(
        PARTITION BY passport
        ORDER BY thoi_diem_cap_nhat DESC, ngay_den DESC
      ) AS rn
    FROM BaseData
  )
  WHERE rn = 1
),

-- 3) Gom khoảng lưu trú (merge intervals)
OrderedIntervals AS (
  SELECT
    *,
    MAX(end_eff) OVER(
      PARTITION BY passport
      ORDER BY ngay_den
      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS prev_max_end
  FROM BaseData
),

IslandTagged AS (
  SELECT
    *,
    CASE WHEN prev_max_end IS NULL OR ngay_den > prev_max_end + INTERVAL 1 DAY THEN 1 ELSE 0 END AS new_island
  FROM OrderedIntervals
),

Islandized AS (
  SELECT
    *,
    SUM(new_island) OVER(
      PARTITION BY passport
      ORDER BY ngay_den
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS island_id
  FROM IslandTagged
),

IslandAgg AS (
  SELECT
    passport,
    island_id,
    MIN(ngay_den) AS island_start,
    COALESCE(MAX(ngay_di), CURRENT_DATE) AS island_end_eff,
    MAX(ngay_di) AS island_end_real,
    STRING_AGG(DISTINCT dia_chi_tam_tru, ' | ') AS island_addresses,
    FIRST(ket_qua_xac_minh ORDER BY thoi_diem_cap_nhat DESC) AS island_ket_qua_xac_minh
  FROM Islandized
  GROUP BY passport, island_id
),

-- 4) Chọn island mới nhất
LatestIsland AS (
  SELECT * EXCLUDE(rn)
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER(
        PARTITION BY passport
        ORDER BY island_end_eff DESC, island_start DESC
      ) AS rn
    FROM IslandAgg
  )
  WHERE rn = 1
),

-- 5) Thống kê 1 năm gần đây
Rolling1Y AS (
  SELECT
    passport,
    SUM(
      CASE
        WHEN island_end_eff < CURRENT_DATE - INTERVAL 365 DAY THEN 0
        ELSE DATEDIFF('day',
          GREATEST(island_start, CURRENT_DATE - INTERVAL 365 DAY),
          LEAST(island_end_eff, CURRENT_DATE)
        ) + 1
      END
    ) AS tong_ngay_1y
  FROM IslandAgg
  GROUP BY passport
),

Arrivals1Y AS (
  SELECT
    passport,
    COUNT(*) FILTER (WHERE ngay_den >= CURRENT_DATE - INTERVAL 365 DAY) AS so_lan_1y
  FROM BaseData
  GROUP BY passport
),

-- 6) Thống kê tích lũy
Lifetime AS (
  SELECT
    passport,
    SUM(DATEDIFF('day', island_start, LEAST(island_end_eff, CURRENT_DATE)) + 1) AS tong_ngay_life
  FROM IslandAgg
  GROUP BY passport
)

SELECT
  P.ho_ten,
  P.ngay_sinh,
  P.quoc_tich,
  L.passport AS so_ho_chieu,
  L.island_start AS ngay_den,
  L.island_end_real AS ngay_di,
  L.island_addresses AS dia_chi_tam_tru,
  COALESCE(A.so_lan_1y, 0) AS so_lan_nhap_canh,
  COALESCE(R.tong_ngay_1y, 0) AS tong_ngay_luu_tru_2025,
  COALESCE(LT.tong_ngay_life, 0) AS tong_ngay_tich_luy,
  
  -- Kết quả xác minh (từ CAX)
  L.island_ket_qua_xac_minh AS ket_qua_xac_minh,
  
  -- Mục đích từ hệ thống
  CASE
    WHEN W.so_ho_chieu IS NOT NULL THEN 'Đối tượng chú ý'
    WHEN LB.so_ho_chieu IS NOT NULL THEN 'Lao động'
    WHEN MR.so_ho_chieu IS NOT NULL THEN 'Kết hôn'
    WHEN ST.so_ho_chieu IS NOT NULL THEN 'Học tập'
    ELSE NULL
  END AS muc_dich_he_thong,
  
  -- Trạng thái cuối cùng (ưu tiên xác minh thủ công)
  COALESCE(
    NULLIF(TRIM(L.island_ket_qua_xac_minh), ''),
    CASE
      WHEN W.so_ho_chieu IS NOT NULL THEN 'Đối tượng chú ý'
      WHEN LB.so_ho_chieu IS NOT NULL THEN 'Lao động'
      WHEN MR.so_ho_chieu IS NOT NULL THEN 'Kết hôn'
      WHEN ST.so_ho_chieu IS NOT NULL THEN 'Học tập'
      ELSE NULL
    END
  ) AS trang_thai_cuoi_cung,
  
  -- Chi tiết
  LB.vi_tri AS labor_vi_tri,
  LB.noi_lam_viec AS labor_noi_lam_viec,
  CONCAT(COALESCE(LB.vi_tri, ''), ' tại ', COALESCE(LB.noi_lam_viec, '')) AS labor_detail,
  
  MR.ho_ten_vn AS marriage_ho_ten_vn,
  MR.dia_chi AS marriage_dia_chi,
  MR.dien AS marriage_dien,
  CONCAT('Vợ/Chồng: ', COALESCE(MR.ho_ten_vn, ''), ' - ', COALESCE(MR.dia_chi, '')) AS marriage_detail,
  
  W.dien AS watchlist_dien,
  W.so_cong_van AS watchlist_so_cong_van,
  W.ngay_nhap AS watchlist_ngay_nhap,
  CONCAT('Diện: ', COALESCE(W.dien, ''), ' - CV: ', COALESCE(W.so_cong_van, '')) AS watchlist_detail

FROM LatestIsland L
JOIN PersonLatest P USING (passport)
LEFT JOIN Rolling1Y R USING (passport)
LEFT JOIN Arrivals1Y A USING (passport)
LEFT JOIN Lifetime LT USING (passport)
LEFT JOIN ref_labor LB ON L.passport = TRIM(UPPER(LB.so_ho_chieu))
LEFT JOIN ref_student ST ON L.passport = TRIM(UPPER(ST.so_ho_chieu))
LEFT JOIN ref_watchlist W ON L.passport = TRIM(UPPER(W.so_ho_chieu))
LEFT JOIN ref_marriage MR ON L.passport = TRIM(UPPER(MR.so_ho_chieu));
"""


def init_database() -> bool:
    """
    Initialize database with schema and default data
    
    Returns:
        True if successful
    """
    conn = get_connection()
    
    # Create tables
    for statement in SCHEMA_SQL.split(';'):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    
    conn.commit()
    
    # Create view
    conn.execute(VIEW_SQL)
    conn.commit()
    
    # Create default admin user if not exists
    result = conn.execute(
        "SELECT COUNT(*) FROM users WHERE username = 'admin'"
    ).fetchone()
    
    if result[0] == 0:
        # Hash the default password
        password_hash = bcrypt.hashpw(
            "admin123".encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        conn.execute(
            """INSERT INTO users (username, password_hash, role, full_name)
               VALUES (?, ?, ?, ?)""",
            ("admin", password_hash, "admin", "Administrator")
        )
        conn.commit()
        print("✅ Created default admin user (username: admin, password: admin123)")
    
    return True


def create_user(username: str, password: str, role: str = "commune", 
                full_name: str = None, email: str = None) -> bool:
    """
    Create a new user
    
    Args:
        username: Unique username
        password: Plain text password (will be hashed)
        role: 'admin' or 'commune'
        full_name: Display name
        email: Email address
        
    Returns:
        True if successful
    """
    conn = get_connection()
    
    # Hash password
    password_hash = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    try:
        conn.execute(
            """INSERT INTO users (username, password_hash, role, full_name, email)
               VALUES (?, ?, ?, ?, ?)""",
            (username, password_hash, role, full_name, email)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False


def verify_user(username: str, password: str) -> dict:
    """
    Verify user credentials
    
    Args:
        username: Username
        password: Plain text password
        
    Returns:
        User dict if valid, None otherwise
    """
    conn = get_connection()
    
    result = conn.execute(
        """SELECT id, username, password_hash, role, full_name, is_active
           FROM users WHERE username = ?""",
        (username,)
    ).fetchone()
    
    if result is None:
        return None
    
    user_id, uname, password_hash, role, full_name, is_active = result
    
    if not is_active:
        return None
    
    # Verify password
    if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
        # Update last login
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        
        return {
            "id": user_id,
            "username": uname,
            "role": role,
            "full_name": full_name
        }
    
    return None
