# CETTP V3.6.4 – Startup Source and Admin Bootstrap Fix

- Repaired the designated environment Admin account when it already exists but is inactive or has a non-admin role.
- Resets the environment password only during that repair and requires a password change at next login.
- Preserves the password of an already-active Admin on normal restarts.
- Kept EFD processing-history HTML in `templates/efd_portal/history.html`; it is not Python source.
- Repacked the project with application files at the ZIP root to reduce extraction/deployment path confusion.
- No database reset, table drop, or production record deletion is included.

Validation: Python compilation, Jinja template parsing, and ZIP integrity checks. No live Render/PostgreSQL login test was performed.
