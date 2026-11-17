# CETTP V3.3.1 — Email Logs schema repair

## What this release fixes

The `/tax-email` page was failing with PostgreSQL `UndefinedColumn` because the
existing `portal_email_logs` table did not contain the `module` column expected
by the `PortalEmailLog` SQLAlchemy model.

The model defines `module` as `VARCHAR(80) NOT NULL` with an index. Calling
SQLAlchemy `create_all()` does not add missing columns to an existing table.

## Required production migration

Before deploying this release, take a PostgreSQL backup/snapshot, then run:

`migrations/V3_3_1_add_portal_email_logs_module.sql`

Run it against the **existing CETTP production database** using the Render
PostgreSQL PSQL connection. The script is idempotent: it adds the column only
if absent, fills historical rows with `general`, applies NOT NULL, and creates
the model's index only if absent. It does not delete, truncate, recreate, or
overwrite existing email-log records.

After running it, verify that `module` is `character varying`, `is_nullable`
is `NO`, and `rows_missing_module` is zero. Then deploy the application.

If the table is not present, stop and investigate the connected database/schema;
do not create a replacement table or reset the database as a workaround.

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
