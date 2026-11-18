# CETTP V3.4.1 – WHT TIN table naming fix

## Fix
- Added an explicit `__tablename__ = "wht_tin_batch"` to `WHTTINBatch`.
- This aligns the registered SQLAlchemy table name with the foreign key used by `WHTTINLedgerRow.batch_id`, resolving `NoReferencedTableError` during `db.create_all()`.

## Data safety
- Additive model metadata correction only.
- No table drop, truncate, database reset, or existing-record deletion is included.
- The existing `wht_tin_ledger_row` table naming is unchanged.

## Verification
- Python syntax compilation and ZIP integrity checked.
- Full Flask/PostgreSQL startup and Render deployment must still be verified in the target environment.
