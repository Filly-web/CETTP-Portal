# V3.6.2 — Admin-Controlled User Access

- Central email/password sign-in.
- Render environment variables bootstrap the first Admin account.
- Admin user management: create users, role assignment/change, activation/deactivation, password reset.
- Initiators and Tax Compliance use assigned credentials; email-only Initiator access and old tax access code are disabled.
- First-login temporary password change required; secure password hashing.
- Authenticated access required for EFD Invoice Processing portal.
- Existing database and workflows retained; new `cettp_users` table only.
