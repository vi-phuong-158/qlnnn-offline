# Bolt's Journal

## 2024-05-22 - [Initial Entry]
**Learning:** Initialized Bolt's journal.
**Action:** Use this to record critical performance learnings.

## 2026-01-31 - [Streamlit Caching & Headless Contexts]
**Learning:** `st.cache_data.clear()` raises an error when called from scripts outside a Streamlit runtime (e.g. data import scripts).
**Action:** Always wrap `st.cache_data.clear()` in a `try...except` block within shared modules to ensure they remain usable in both web and script contexts.
