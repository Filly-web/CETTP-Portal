-- CETTP V3.8.2: additive EFD reconciliation indexes.
-- Safe to run repeatedly on PostgreSQL; no existing records or tables are changed.
CREATE INDEX IF NOT EXISTS ix_efd_recon_batches_period_source_current
    ON efd_recon_batches (period, source, is_current);
CREATE INDEX IF NOT EXISTS ix_efd_recon_rows_batch_code
    ON efd_recon_rows (batch_id, verification_code);
CREATE INDEX IF NOT EXISTS ix_efd_recon_batches_file_digest
    ON efd_recon_batches (file_sha256);
