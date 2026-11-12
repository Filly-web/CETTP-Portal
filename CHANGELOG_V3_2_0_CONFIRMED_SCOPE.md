# CETTP V3.2.0 – Investment WHT, Central Email and Cancellation Tracker

## Release scope delivered

### Investment WHT Credits
- Existing investment registrations can be edited, with recalculation of interest and expected WHT.
- Individual investment deletion removes its reminder email logs.
- Imported batch deletion removes only investments linked to that batch and their reminder logs. Manual registrations and other batches are retained.
- Delete actions use browser confirmation prompts.
- Existing investment reconciliation and certificate workflows are retained.

### Central Yahoo email service
- All portal email sends use one shared SMTP delivery function.
- Defaults: `smtp.mail.yahoo.com:587`, sender/login `temporarytin2026@yahoo.com`.
- SMTP password is read only from `SMTP_PASSWORD`; it is not stored in source code.
- Every send attempt, including test attempts, is recorded in `portal_email_logs`.
- The Investment WHT page includes a test-email action and a recent email activity table.
- Investment reminder logs and case notification logs remain available in their existing tables.

### Cancellation Tracker
- Premium Register upload and review remain separate workflow sections.
- Automatic classifications are retained: matched amount, potential endorsement (different amount), and pure cancellation.
- Classification can be corrected manually before CETTP case import.
- Classification filters, category counts, 10-row pagination, previous/next navigation, and page-level selection are provided.
- Import can target selected rows or all unimported rows in one classification.
- Existing duplicate-action detection and case-linking prevent duplicate CETTP imports.

### Existing CETTP and deployment safety
- Existing modules, routes, case workflows, and database configuration are retained.
- The existing PostgreSQL `DATABASE_URL` is not changed.
- No production data deletion or database reset is part of this release.
- `db.create_all()` creates the new email-log table if absent; it does not drop or recreate existing tables.
- Existing Render service and deployment files are retained. Deploy this archive to the existing service; do not create a replacement service or attach a new database.

## Render environment variables

Set/update these variables in the existing Render service:

| Variable | Value |
|---|---|
| `SMTP_HOST` | `smtp.mail.yahoo.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `temporarytin2026@yahoo.com` |
| `SMTP_FROM` | `temporarytin2026@yahoo.com` |
| `SMTP_PASSWORD` | Yahoo-generated App Password (store as a secret in Render) |
| `CETTP_TAX_COMPLIANCE_EMAIL` | Approved notification recipient(s), comma or semicolon separated |
| `CETTP_INVESTMENT_WHT_EMAIL` | Optional separate WHT recipient(s); falls back to `CETTP_TAX_COMPLIANCE_EMAIL` |
| `CETTP_BASE_URL` | Existing public CETTP URL |
| `INVESTMENT_WHT_CRON_TOKEN` | Existing strong cron token; retain current value if already configured |

Do not commit a Yahoo App Password to Git, the ZIP, `.env.example`, or application source. Generate the App Password from the Yahoo account security settings and enter it directly into Render's secret environment variable field.

The application uses STARTTLS on port 587. Confirm that the Yahoo account is authorized to send from the configured sender address.

## Deployment procedure – preserve production

1. Take a current PostgreSQL backup/snapshot using the existing approved Render process.
2. Update the existing Render service with this release. Keep the existing service, environment, `DATABASE_URL`, build command, start command, and persistent configuration unchanged.
3. Add/update the SMTP variables above. Do not replace `SECRET_KEY`, `DATABASE_URL`, `TAX_ACCESS_CODE`, or existing cron tokens unless there is a separately approved rotation.
4. Deploy and wait for the health check to pass.
5. Sign in as Tax Compliance and verify:
   - Investment register loads; edit one test registration and cancel before saving if not intended.
   - Individual and batch delete confirmation prompts appear. Use only a controlled test record if testing deletion.
   - Central email test sends to the approved recipient and appears in Recent portal email activity.
   - Cancellation upload, classification correction, filters, 10-row pagination, page selection, and classification-based import work.
   - Existing CETTP case register, case detail, Initiator workflow, VAT control account, and other existing modules remain accessible.
6. Verify the existing PostgreSQL data remains present. Do not run `DROP`, `TRUNCATE`, or destructive migration commands.

## Verification notes
- `app.py` passes Python bytecode compilation.
- Automated unit tests could not be executed in the build environment because Flask is not installed there. Run `python -m unittest discover -s tests` in the application's normal dependency environment after installing `requirements.txt`.
