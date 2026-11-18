# CETTP V3.4.5 — Email audit `event_type` repair

This update addresses the production error where inserting a central email audit record failed because PostgreSQL requires `portal_email_logs.event_type`, but the application model and insert did not supply it.

Changes:
- Adds `event_type` to the `PortalEmailLog` SQLAlchemy model.
- Sets `event_type` from the normalized email event key whenever a central email audit record is created.
- Extends the additive startup migration to add/backfill `event_type`, enforce its non-null requirement, and create its index.
- Includes an idempotent PostgreSQL SQL fallback at `migrations/V3_4_5_repair_portal_email_logs_event_type.sql`.

Existing email audit records and other CETTP data are retained. No table is dropped or recreated. This package has not been deployed to the live Render service; test it after deployment.

## Deployment
1. Keep the existing Render service and `DATABASE_URL`; do not create a replacement database.
2. Deploy this ZIP to the existing service.
3. Check Render logs for `Portal email log schema check completed (all expected columns verified)`.
4. Open `/tax-email` and run the email configuration test again.
5. If startup migration reports a database permission error, have the PostgreSQL database owner run the included SQL file against the same production database.

Keep existing SMTP environment variables unchanged. Yahoo credentials remain environment variables and are not included in this ZIP.
