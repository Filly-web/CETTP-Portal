-- CETTP V3.3.1: repair portal_email_logs schema drift.
-- Safe to run more than once. Preserves all existing records.
-- Run against the existing production PostgreSQL database before deploying
-- the application version that queries PortalEmailLog.module.

BEGIN;

ALTER TABLE IF EXISTS portal_email_logs
    ADD COLUMN IF NOT EXISTS module VARCHAR(80);

UPDATE portal_email_logs
   SET module = 'general'
 WHERE module IS NULL;

ALTER TABLE IF EXISTS portal_email_logs
    ALTER COLUMN module SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_portal_email_logs_module
    ON portal_email_logs (module);

COMMIT;

-- Verification:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = current_schema()
--   AND table_name = 'portal_email_logs'
--   AND column_name = 'module';
--
-- SELECT COUNT(*) AS rows_missing_module
-- FROM portal_email_logs
-- WHERE module IS NULL;
