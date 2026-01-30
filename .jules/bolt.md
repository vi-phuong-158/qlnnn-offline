# Bolt's Journal

## 2024-05-22 - [Initial Entry]
**Learning:** Initialized Bolt's journal.
**Action:** Use this to record critical performance learnings.

## 2024-05-22 - [Streamlit Caching Strategy]
**Learning:** This Streamlit app re-calculates complex SQL stats on every rerender (interaction). Since it's an "Offline" app where data only changes via specific "Import" actions, we can aggressively cache stats using `@st.cache_data` and manually clear it (`st.cache_data.clear()`) only during the Import workflow.
**Action:** For read-heavy Streamlit apps with infrequent writes, prefer long TTL caching combined with manual invalidation triggers at the write source.
