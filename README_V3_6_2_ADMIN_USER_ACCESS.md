# CETTP V3.6.2 — Admin-Controlled User Access

## Features
- Initial administrator bootstrapped from Render environment variables (only when the email does not already exist).
- Admin user-management page to create users, assign roles, change roles, activate/deactivate accounts, and reset passwords.
- User sign-in using registered work email and password.
- Passwords stored as Werkzeug secure hashes; never stored as plain text.
- Minimum 12-character passwords for new/reset passwords.
- Temporary passwords require password change on first sign-in.
- Initiator access is now authenticated; previous email-only initiator access is disabled.
- Existing Tax Access Code route redirects to centralized login; the legacy code is no longer accepted.
- EFD invoice-processing portal redirects unauthenticated users to centralized login.
- Admin account uses the Tax Compliance workspace permissions plus an Admin flag for User Management.
- User data table is additive (`cettp_users`); startup bootstrap does not overwrite existing account password or role.
- Prevents an administrator from deactivating or demoting their own active admin account, and prevents lockout by disabling/demoting the last active admin.

## Render Environment Variables
Set these at Render before first deployment:
- `CETTP_ADMIN_EMAIL` — initial Admin's work email
- `CETTP_ADMIN_PASSWORD` — initial Admin temporary password (minimum 12 characters)
- `CETTP_ADMIN_NAME` — optional full name (default: CETTP Administrator)

The existing `SECRET_KEY` and `DATABASE_URL` should remain unchanged. Never commit real passwords or secrets.


## Important migration behavior
- The new table is created additively by `db.create_all()`.
- No existing application tables, records, EFD requests, uploads, or PostgreSQL data are deleted or reset.
- Initial Admin is inserted only if the environment email is not already registered. Changing the environment password later will not reset an existing user's password.

## Test status
Static Python compilation and Jinja template parsing are performed in this build. Live Render/PostgreSQL/browser sign-in tests are not possible in this environment.
