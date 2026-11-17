# CETTP V2.9.2 – Safe Premium Register Batch Deletion

## Batch deletion changes
- Replaced the previous ORM/case-deletion sequence with a database-side delete scoped to the selected upload's unique `upload_batch` key.
- The selected `RegisterUpload` and its `CancellationTrack` rows are deleted in one database transaction.
- CETTP `Case` records are deliberately retained. A case may be shared by another Premium Register batch or contain audit logs, attachments and notifications; batch deletion must not delete formal case history.
- If any database operation fails, the transaction is rolled back and no partial deletion is committed.
- Full exception details are written to the Render application log. The user receives a timestamp reference to help locate the relevant log entry.
- Updated the confirmation prompt and success message to explain that CETTP cases are retained.
- Updated `/health` version to `2.9.2-safe-batch-delete`.

## Database and deployment safety
- No database schema migration is included.
- No `DATABASE_URL`, database attachment, Render service, or production data is changed by this source package.
- No FAR module or FAR navigation is included.

## Regression test
`tests/test_batch_delete.py` tests deletion against an isolated in-memory SQLite database, including a case shared by two batches. Run with `python -m unittest discover -s tests` in an environment with the requirements installed.
