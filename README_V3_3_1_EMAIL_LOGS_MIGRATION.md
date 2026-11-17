# CETTP V3.3.1 — Email Logs schema repair

## What this release fixes

The `/tax-email` page was failing with PostgreSQL `UndefinedColumn` because the
existing `portal_email_logs` table did not contain the `module` column expected
by the `PortalEmailLog` SQLAlchemy model.

The model defines `module` as `VARCHAR(80) NOT NULL` with an index. Calling
SQLAlchemy `create_all()` does not add missing columns to an existing table.

## Automatic production schema repair (V3.3.2)

This release now performs a narrowly scoped, idempotent schema check at
application startup, immediately after `db.create_all()`. If the existing
`portal_email_logs` table is missing `module`, the application adds it as
`VARCHAR(80) NOT NULL DEFAULT 'general'`, backfills legacy NULL values, and
creates the module index if needed. Existing email-log rows are preserved.

Before deploying, take a PostgreSQL backup/snapshot. The application database
user must have permission to ALTER the `portal_email_logs` table and create an
index. If it lacks those permissions, the migration failure is recorded in
Render logs; the portal will still start, but `/tax-email` will remain
unavailable until the schema is repaired. The manual SQL script remains
available at `migrations/V3_3_1_add_portal_email_logs_module.sql` as a fallback.

After deployment, check Render logs for `Portal email log schema check
completed`, then open `/tax-email`. If the migration fails, use the logged
exception to identify the missing database permission or schema issue.

## Other CETTP functionality

This release is based on the prior V3.3.0 complete release and retains its
existing modules and workflows, including the central Yahoo SMTP configuration,
Investment WHT Credits, and Cancellation Tracker changes. Yahoo SMTP remains
the configured provider; no alternative email provider is introduced.

## Yahoo SMTP environment variables

Configure these in the existing Render web service environment:

- `SMTP_HOST=smtp.mail.yahoo.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=temporarytin2026@yahoo.com`
- `SMTP_FROM=temporarytin2026@yahoo.com`
- `SMTP_PASSWORD` = Yahoo-generated App Password (store only in Render)
- `CETTP_TAX_COMPLIANCE_EMAIL` = intended compliance notification recipient

Keep credentials out of source control and ZIP files. The migration does not
change SMTP connectivity or bypass provider/network timeouts.

## Validation scope

The release package should be checked for ZIP integrity, Python syntax, and
Jinja template compilation. These checks do not replace deployment-time
database verification, full Flask integration tests, or a live Yahoo SMTP
connectivity test.
