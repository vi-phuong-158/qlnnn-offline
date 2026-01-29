"""
QLNNN Offline - Main Application
Streamlit Entry Point
"""

import streamlit as st
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.models import init_database, verify_user
from config import ROLE_PERMISSIONS, SESSION_TTL_HOURS

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="QLNNN Offline - Tra cứu NNN",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1e3a5f;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    /* Cards */
    .result-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #6c757d;
    }
    
    .result-card.watchlist {
        border-left-color: #dc3545;
        background-color: #fff5f5;
    }
    
    .result-card.labor {
        border-left-color: #ffc107;
        background-color: #fffbeb;
    }
    
    .result-card.marriage {
        border-left-color: #28a745;
        background-color: #f0fff4;
    }
    
    .result-card.student {
        border-left-color: #17a2b8;
        background-color: #f0f9ff;
    }
    
    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }
    
    .stat-card h2 {
        font-size: 2.5rem;
        margin: 0;
    }
    
    .stat-card p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Login form */
    .login-container {
        max-width: 400px;
        margin: 4rem auto;
        padding: 2rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================
# SESSION STATE INIT
# ============================================

if "authenticated" not in st.session_state:
    # TEMP: Auto-authenticate for testing
    st.session_state.authenticated = True
    st.session_state.user = {"username": "admin", "full_name": "Admin (Test)", "role": "admin"}

if "db_initialized" not in st.session_state:
    st.session_state.db_initialized = False

# ============================================
# DATABASE INITIALIZATION
# ============================================

if not st.session_state.db_initialized:
    with st.spinner("Đang khởi tạo database..."):
        try:
            init_database()
            st.session_state.db_initialized = True
        except Exception as e:
            st.error(f"Lỗi khởi tạo database: {e}")
            st.stop()

# ============================================
# AUTHENTICATION
# ============================================

def login():
    """Display login form and handle authentication"""
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>🌏 QLNNN Offline</h1>
        <p style="color: #666;">Hệ thống tra cứu & quản lý người nước ngoài</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Đăng nhập")
            
            username = st.text_input("Tên đăng nhập", placeholder="Nhập username")
            password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Vui lòng nhập đầy đủ thông tin")
                else:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Xin chào, {user['full_name'] or user['username']}!")
                        st.rerun()
                    else:
                        st.error("Sai tên đăng nhập hoặc mật khẩu")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 1rem; color: #666; font-size: 0.9rem;">
            <p>Tài khoản mặc định: admin / admin123</p>
            <p>⚠️ Vui lòng đổi mật khẩu sau khi đăng nhập lần đầu</p>
        </div>
        """, unsafe_allow_html=True)


def logout():
    """Clear session and logout"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()


# ============================================
# SIDEBAR
# ============================================

def show_sidebar():
    """Display sidebar with user info and navigation"""
    
    with st.sidebar:
        # User info
        user = st.session_state.user
        st.markdown(f"""
        <div style="padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 1rem;">
            <p style="color: white; margin: 0;">👤 <strong>{user['full_name'] or user['username']}</strong></p>
            <p style="color: #aaa; margin: 0.25rem 0 0 0; font-size: 0.85rem;">
                {'🛡️ Admin' if user['role'] == 'admin' else '🏛️ Công an xã'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### 📌 Menu")
        
        # Logout button
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout()


# ============================================
# MAIN PAGE CONTENT
# ============================================

def show_home():
    """Display home page with quick stats"""
    
    st.title("🌏 QLNNN Offline")
    st.markdown("### Hệ thống tra cứu & quản lý người nước ngoài (Offline)")
    
    st.markdown("---")
    
    # Quick stats
    from modules.statistics import get_statistics, get_last_update_time
    
    stats = get_statistics()
    last_update = get_last_update_time()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="👥 Tổng số NNN",
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
            label="⚠️ Đối tượng chú ý",
            value=stats['watchlist_count'],
            delta="Cần theo dõi" if stats['watchlist_count'] > 0 else None,
            delta_color="inverse"
        )
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### 🚀 Truy cập nhanh")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.page_link("pages/1_📊_Tra_cuu.py", label="📊 Tra cứu", icon="🔍")
    
    with col2:
        st.page_link("pages/2_📈_Thong_ke.py", label="📈 Thống kê", icon="📈")
    
    with col3:
        if st.session_state.user['role'] == 'admin':
            st.page_link("pages/3_📥_Import.py", label="📥 Import dữ liệu", icon="📥")
        else:
            st.info("Cần quyền Admin")
    
    with col4:
        st.page_link("pages/4_⚙️_Cai_dat.py", label="⚙️ Cài đặt", icon="⚙️")
    
    st.markdown("---")
    
    # Info
    st.info(f"📅 Dữ liệu cập nhật lần cuối: **{last_update}**")
    
    st.markdown("""
    ### 📋 Hướng dẫn sử dụng
    
    1. **Tra cứu**: Tìm kiếm thông tin NNN theo số hộ chiếu hoặc họ tên
    2. **Tra cứu hàng loạt**: Nhập nhiều số hộ chiếu để tra cứu cùng lúc
    3. **Thống kê**: Xem báo cáo tổng hợp theo thời gian, quốc tịch, mục đích
    4. **Import**: (Admin) Nhập dữ liệu mới từ file Excel/CSV
    5. **Export**: Xuất kết quả tra cứu ra file Excel
    
    ---
    
    *Phiên bản: 1.0.0 | Python Offline Edition*
    """)


# ============================================
# MAIN APP
# ============================================

def main():
    if not st.session_state.authenticated:
        login()
    else:
        show_sidebar()
        show_home()


if __name__ == "__main__":
    main()
