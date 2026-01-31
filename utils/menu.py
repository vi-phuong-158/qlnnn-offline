import streamlit as st

def menu():
    """Render the sidebar menu with correct Vietnamese labels"""
    
    # User info
    if "user" in st.session_state and st.session_state.user:
        user = st.session_state.user
        st.sidebar.markdown(f"""
        <div style="padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 1rem;">
            <p style="color: white; margin: 0;">👤 <strong>{user.get('full_name') or user.get('username')}</strong></p>
            <p style="color: #aaa; margin: 0.25rem 0 0 0; font-size: 0.85rem;">
                {'🛡️ Admin' if user.get('role') == 'admin' else '🏛️ Công an xã'}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("### 📌 Menu")
    
    st.sidebar.page_link("Trang_chu.py", label="Trang chủ", icon="🏠")
    st.sidebar.page_link("pages/1_📊_Tra_cuu.py", label="Tra cứu", icon="🔍")
    st.sidebar.page_link("pages/2_📈_Thong_ke.py", label="Thống kê", icon="📈")
    
    if "user" in st.session_state and st.session_state.user and st.session_state.user.get("role") == "admin":
        st.sidebar.page_link("pages/3_📥_Nhap_lieu.py", label="Nhập liệu", icon="📥")
        
    st.sidebar.page_link("pages/4_⚙️_Cai_dat.py", label="Cài đặt", icon="⚙️")
    
    st.sidebar.markdown("---")
    
    # Import logout function from app/Trang_chu? 
    # Avoiding circular import by re-implementing logout here or passing it?
    # Simple way: just clear session
    if st.sidebar.button("🚪 Đăng xuất", key="logout_btn", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.session_start = None
        st.rerun()
