# V3.3.1 — Email Logs schema repair

- Added an idempotent PostgreSQL migration for `portal_email_logs.module`.
- Backfills existing records with `general` before enforcing `NOT NULL`.
- Adds the `module` index expected by the SQLAlchemy model.
- Includes production migration and verification instructions.
- Retains Yahoo SMTP and the existing CETTP modules; no production data reset.
