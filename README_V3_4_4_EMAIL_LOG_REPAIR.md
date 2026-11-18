# CETTP V3.4.4 — Email Log repair deployment notes

The deployed application was selecting `portal_email_logs.event_key`, but the production PostgreSQL table did not contain that column. This package corrects the startup migration so it verifies and additively repairs the full `PortalEmailLog` schema, not only the previously handled `module` column.

The migration runs after `db.create_all()` and is safe to repeat. It only adds missing columns, fills null legacy values in those columns, and creates indexes. Existing email-log entries are retained.

No Yahoo SMTP credentials are included in this ZIP. Keep the existing Render environment variables unchanged:
- `SMTP_HOST=smtp.mail.yahoo.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=temporarytin2026@yahoo.com`
- `SMTP_FROM=temporarytin2026@yahoo.com`
- `SMTP_PASSWORD` = existing Yahoo App Password configured in Render
- `CETTP_TAX_COMPLIANCE_EMAIL` = existing notification recipient(s)

## Deploy and test
1. Back up/snapshot the Render PostgreSQL database.
2. Deploy the package to the existing Render service, without changing `DATABASE_URL`.
3. Confirm the startup log states `Portal email log schema check completed (all expected columns verified)`.
4. Visit the Email Log page (`/tax-email`).
5. Confirm historical log entries remain available.

If automatic migration is blocked by database permissions, run `migrations/V3_4_4_repair_portal_email_logs.sql` using the production database owner. Never drop the table or reset the database for this issue.
