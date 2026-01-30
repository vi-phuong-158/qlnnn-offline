## 2024-05-22 - Streamlit Search Interaction
**Learning:** Streamlit's decoupled text_input and button components break the standard 'Enter to search' user expectation, causing friction.
**Action:** proactively wrap search input/button pairs in `st.form` to enable native keyboard submission.
