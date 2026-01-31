"""
QLNNN Offline - Trang Cài đặt
Quản lý users, đổi mật khẩu
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import create_user, verify_user
from database.connection import get_connection, execute_query
from utils.security import hash_password, is_strong_password
from utils.menu import menu

st.set_page_config(page_title="Cài đặt - QLNNN", page_icon="⚙️", layout="wide")

# Auth check
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("⚠️ Vui lòng đăng nhập")
    st.stop()

menu()

st.title("⚙️ Cài đặt")

user = st.session_state.user
is_admin = user.get("role") == "admin"

tab1, tab2 = st.tabs(["🔐 Đổi mật khẩu", "👥 Quản lý Users" if is_admin else "👤 Thông tin"])

# TAB 1: Change Password
with tab1:
    st.markdown("### 🔐 Đổi mật khẩu")
    
    with st.form("change_password"):
        current_pw = st.text_input("Mật khẩu hiện tại", type="password")
        new_pw = st.text_input("Mật khẩu mới", type="password")
        confirm_pw = st.text_input("Xác nhận mật khẩu mới", type="password")
        
        if st.form_submit_button("Đổi mật khẩu"):
            if not all([current_pw, new_pw, confirm_pw]):
                st.error("Vui lòng điền đầy đủ")
            elif new_pw != confirm_pw:
                st.error("Mật khẩu mới không khớp")
            elif len(new_pw) < 6:
                st.error("Mật khẩu phải có ít nhất 6 ký tự")
            else:
                # Verify current password
                verified = verify_user(user["username"], current_pw)
                if not verified:
                    st.error("Mật khẩu hiện tại không đúng")
                else:
                    # Update password
                    conn = get_connection()
                    new_hash = hash_password(new_pw)
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (new_hash, user["id"])
                    )
                    conn.commit()
                    st.success("✅ Đổi mật khẩu thành công!")

# TAB 2: User Management (Admin only)
with tab2:
    if is_admin:
        st.markdown("### 👥 Quản lý Users")
        
        # List users
        users = execute_query("SELECT id, username, role, full_name, is_active FROM users")
        
        if users:
            import pandas as pd
            df = pd.DataFrame(users)
            df["is_active"] = df["is_active"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Add new user
        st.markdown("#### ➕ Thêm user mới")
        
        with st.form("add_user"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
            with col2:
                new_fullname = st.text_input("Họ tên")
                new_role = st.selectbox("Role", ["commune", "admin"])
            
            if st.form_submit_button("Thêm user"):
                if not new_username or not new_password:
                    st.error("Username và Password bắt buộc")
                else:
                    success = create_user(new_username, new_password, new_role, new_fullname)
                    if success:
                        st.success(f"✅ Đã thêm user {new_username}")
                        st.rerun()
                    else:
                        st.error("Username đã tồn tại")
    else:
        st.markdown("### 👤 Thông tin tài khoản")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Họ tên:** {user.get('full_name', 'N/A')}")
        st.write(f"**Role:** {user['role']}")
