# CETTP V3.3.2 — Automatic Email Logs schema repair

- Adds an idempotent startup schema check after `db.create_all()`.
- If `portal_email_logs.module` is missing, adds it as `VARCHAR(80) NOT NULL DEFAULT 'general'`.
- Backfills any legacy NULL values to `general`, enforces NOT NULL on PostgreSQL, and creates the module index if missing.
- Does not delete, truncate, recreate, or overwrite existing email-log records.
- Migration failures are logged with a traceback; the application is allowed to start so other portal functions remain available. The Email Logs page may remain unavailable until the database permission/schema issue is resolved.
- No SMTP provider or credentials are changed.
