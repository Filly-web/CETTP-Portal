# CETTP V3.4.4 — Email Log schema compatibility repair

- Fixes the `/tax-email` HTTP 500 caused by PostgreSQL reporting that `portal_email_logs.event_key` does not exist.
- Replaces the earlier module-only startup check with an idempotent additive schema check for all columns expected by the current `PortalEmailLog` model.
- Adds missing columns, backfills safe values for legacy rows, enforces required-column constraints on PostgreSQL, and ensures the expected indexes exist.
- Preserves all existing portal email-log rows and all unrelated CETTP tables and records. No table is dropped, truncated, or recreated.
- Does not change Yahoo SMTP settings, sender configuration, passwords, recipients, or email-delivery behavior.
- Includes a standalone PostgreSQL SQL fallback at `migrations/V3_4_4_repair_portal_email_logs.sql`.

## Deployment verification

1. Deploy this ZIP to the existing Render web service using the same database/environment variables.
2. Check Render logs for: `Portal email log schema check completed (all expected columns verified)`.
3. Open `/tax-email`. Confirm that the page loads and existing email-log rows remain visible.
4. Trigger a test email only if desired; SMTP delivery is separate from the database schema repair.

If Render logs show a migration permission error, have the database owner run the included SQL script against the production database. Do not reset or recreate the database.
