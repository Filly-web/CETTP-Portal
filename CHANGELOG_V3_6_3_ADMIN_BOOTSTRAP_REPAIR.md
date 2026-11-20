# CETTP V3.6.3 — Admin Bootstrap Repair

- Fixes the environment-configured administrator login issue where an existing inactive account was not repaired because bootstrap only created accounts when the email was absent.
- For the exact email in `CETTP_ADMIN_EMAIL`, an existing inactive account or account with a non-admin role is reactivated/elevated and its password reset to `CETTP_ADMIN_PASSWORD` (minimum 12 characters), with forced password change on next login.
- If the designated account is already active as Admin, its password is preserved across app restarts.
- No other user accounts are modified. No database reset or destructive schema change is introduced.

## Validation
- Python compilation passed for `app.py`, `efd_portal.py`, and `calendar_reminders.py`.
- Jinja syntax parse passed for all templates.
- ZIP integrity passed.
- No live Render/PostgreSQL/browser login test was performed.
