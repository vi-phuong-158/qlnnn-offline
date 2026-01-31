## 2026-01-29 - Critical Debug Backdoor Found
**Vulnerability:** Found a hardcoded debug block in `app.py` that auto-authenticates any user as Admin, bypassing login entirely.
**Learning:** Debug code left in production entry points is a critical risk that negates all other security controls.
**Prevention:** Never commit "TEMP" or "DEBUG" bypass blocks to the main branch. Use environment variables or separate debug configs that default to secure states.

## 2026-01-30 - Hardcoded Admin Credentials
**Vulnerability:** Found "admin123" hardcoded as the default password in `database/models.py`, which is a common target for dictionary attacks.
**Learning:** Default credentials intended for "convenience" in offline apps often become permanent vulnerabilities if not forced to change or randomly generated.
**Prevention:** Implement "secure by default" initialization: generate random passwords if no environment variable is provided, and never ship code with known default passwords.
