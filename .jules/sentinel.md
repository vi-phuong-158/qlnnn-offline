## 2026-01-29 - Critical Debug Backdoor Found
**Vulnerability:** Found a hardcoded debug block in `app.py` that auto-authenticates any user as Admin, bypassing login entirely.
**Learning:** Debug code left in production entry points is a critical risk that negates all other security controls.
**Prevention:** Never commit "TEMP" or "DEBUG" bypass blocks to the main branch. Use environment variables or separate debug configs that default to secure states.
