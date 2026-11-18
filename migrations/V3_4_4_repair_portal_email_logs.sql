-- CETTP V3.4.4: additive repair for portal_email_logs.
-- Run against the same PostgreSQL database used by the Render web service.
-- Safe to run repeatedly. Existing rows are preserved.

ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS module VARCHAR(80) NOT NULL DEFAULT 'general';
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS event_key VARCHAR(100) NOT NULL DEFAULT 'legacy';
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS reference_id INTEGER;
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS recipient VARCHAR(1000) NOT NULL DEFAULT '';
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS subject VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'unknown';
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS error_message VARCHAR(2000);
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE portal_email_logs ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP;

UPDATE portal_email_logs SET module = 'general' WHERE module IS NULL;
UPDATE portal_email_logs SET event_key = 'legacy' WHERE event_key IS NULL;
UPDATE portal_email_logs SET recipient = '' WHERE recipient IS NULL;
UPDATE portal_email_logs SET subject = '' WHERE subject IS NULL;
UPDATE portal_email_logs SET status = 'unknown' WHERE status IS NULL;
UPDATE portal_email_logs SET attempts = 0 WHERE attempts IS NULL;
UPDATE portal_email_logs SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;

ALTER TABLE portal_email_logs ALTER COLUMN module SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN event_key SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN recipient SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN subject SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN status SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN attempts SET NOT NULL;
ALTER TABLE portal_email_logs ALTER COLUMN created_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_portal_email_logs_module ON portal_email_logs (module);
CREATE INDEX IF NOT EXISTS ix_portal_email_logs_event_key ON portal_email_logs (event_key);
CREATE INDEX IF NOT EXISTS ix_portal_email_logs_reference_id ON portal_email_logs (reference_id);
CREATE INDEX IF NOT EXISTS ix_portal_email_logs_status ON portal_email_logs (status);
CREATE INDEX IF NOT EXISTS ix_portal_email_logs_created_at ON portal_email_logs (created_at);
