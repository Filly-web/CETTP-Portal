# Deploying CETTP V3.6.3 Admin Bootstrap Repair

Use this release to repair the environment-designated Admin account.


1. Replace the deployed source with this package, keeping Render service settings and the existing PostgreSQL database unchanged.
2. Confirm these Render variables: `CETTP_ADMIN_EMAIL`, `CETTP_ADMIN_NAME`, and `CETTP_ADMIN_PASSWORD` (password at least 12 characters).
3. Deploy/restart the service.
4. Sign in using the configured email and environment password. If the account was inactive or had a non-admin role, it will be repaired and must change its temporary password on first sign-in.
5. If it still fails, inspect Render logs for bootstrap warnings/errors; do not reset or delete the production database.

An already active Admin account is not password-reset on every startup. The repair targets only the configured email and does not modify other users.
