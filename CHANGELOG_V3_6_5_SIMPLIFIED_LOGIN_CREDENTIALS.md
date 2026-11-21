# CETTP V3.6.5 – Simplified Login Credentials

## Changes
- Initiator credentials: exactly four numeric digits.
- Tax Compliance and Admin credentials: minimum eight characters.
- First-login password change is no longer mandatory for any role.
- Login rate-limiting and temporary account lockout are not enabled.
- Admin can create users and reset credentials using role-specific validation.
- Environment Admin bootstrap now accepts an eight-character minimum and does not force a first-login change.
- Password/PIN hashing remains enabled; credentials are never stored as plain text.
- Existing PostgreSQL schema and business workflows are unchanged.

## Validation
- Python compilation passed for app.py, efd_portal.py and calendar_reminders.py.
- All 33 Jinja templates parsed successfully.
- ZIP integrity check passed.
- No live Render or production database test was performed.
