# CETTP V2.9.3 – Premium Register batch-delete foreign-key fix

## What this fixes

The Premium Register batch-delete route now deletes only the `CancellationTrack` rows belonging to the selected `RegisterUpload.upload_batch`, then deletes that upload-history row, in one database transaction. It deliberately does **not** delete any `Case` records. This removes the `cancellation_track_case_id_fkey` references before the transaction completes while preserving CETTP cases, attachments, notifications and audit history.

If any step fails, the transaction is rolled back and the exception is logged. No database schema migration is required.

## Deploy to the existing Render service

1. Back up the existing production database.
2. Extract this ZIP. Its contents (`app.py`, `requirements.txt`, `Procfile`, `runtime.txt`, `templates/`, `static/`, etc.) are at the ZIP root.
3. Replace the files in the **existing CETTP GitHub repository** with these extracted files. Do not create a new Render service or database.
4. Keep the existing Render environment variables and database attachment unchanged. In particular, do not modify `DATABASE_URL` or `SECRET_KEY`.
5. Keep the existing build command `pip install -r requirements.txt` and start command `gunicorn app:app`.
6. Deploy the existing Render service.
7. Open `/health`. It must report version `2.9.3-fk-batch-delete` before testing the delete operation.
8. First test with a non-critical Premium Register upload. Confirm that its tracker rows and upload-history entry are removed, while linked CETTP Cases remain in the Case Register.

## Important

- CETTP-only package. No Fixed Asset Governance/FAR module or integration is included.
- No database schema changes or data migration are required.
- Do not delete any production batch until the new `/health` version is visible and the test succeeds.
- A successful local syntax check is not a substitute for testing against the existing Render PostgreSQL database.
