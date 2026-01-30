## 2026-01-29 - Critical Debug Backdoor Found
**Vulnerability:** Found a hardcoded debug block in `app.py` that auto-authenticates any user as Admin, bypassing login entirely.
**Learning:** Debug code left in production entry points is a critical risk that negates all other security controls.
**Prevention:** Never commit "TEMP" or "DEBUG" bypass blocks to the main branch. Use environment variables or separate debug configs that default to secure states.

## 2026-02-14 - Hardcoded Admin Credentials
**Vulnerability:** Default admin password "admin123" was hardcoded in `config.py` and displayed on the login screen.
**Learning:** Even for offline apps, hardcoded credentials in source code are a critical risk as they persist in version control.
**Prevention:** Use environment variables for initial credentials. If missing, generate a secure random password on startup and display it to the operator via stdout/logs.
