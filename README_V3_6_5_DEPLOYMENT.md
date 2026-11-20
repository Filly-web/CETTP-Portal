# CETTP V3.6.5 Deployment

1. Back up the current source and retain the existing Render PostgreSQL database.
2. Replace the application source with the contents of this ZIP at the application root (do not deploy as a nested `cettp_v364` directory).
3. Keep `DATABASE_URL` and `SECRET_KEY` unchanged.
4. Keep `CETTP_ADMIN_EMAIL`, `CETTP_ADMIN_NAME` and `CETTP_ADMIN_PASSWORD` configured. The Admin password must be at least 8 characters.
5. Deploy and test the configured Admin account first.
6. From User Management, create Initiators with exactly four numeric digits and Tax Compliance/Admin users with passwords of at least eight characters.

Initiators are not forced to change their PIN at first login. No login rate limit or temporary lockout is enabled. PINs and passwords continue to be securely hashed in the database.

This package does not reset or delete PostgreSQL records. Live deployment and authentication against production have not been tested in this build environment.
