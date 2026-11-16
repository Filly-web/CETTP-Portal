# Britam CETTP V3.3.0 – Complete Release

## Implemented in this package
- Central Yahoo SMTP delivery service shared by case workflow and Investment WHT reminders.
- SMTP configuration via Render environment variables; no credentials embedded in source.
- Central `portal_email_logs` audit table, email settings page and test-email route.
- Individual Investment WHT edit/delete and safe imported-batch deletion, including associated reminder logs.
- Cancellation tracker classification filter and correction, 10-row pagination, page selection, selected import and import-all-by-classification.
- Single `scripts` block in the cancellation tracker template. The supplied V3.1.0 source template did not contain the duplicate block shown in the earlier V3.2 traceback; the release now adds one scripts block only.
- Existing PostgreSQL data and existing tables are retained. `db.create_all()` creates the new email log table if absent; it does not drop or reset tables.

## Render environment variables
- `SMTP_HOST=smtp.mail.yahoo.com`
- `SMTP_PORT=587`
- `SMTP_USERNAME=temporarytin2026@yahoo.com`
- `SMTP_PASSWORD=<Yahoo-generated App Password>`
- `SMTP_FROM=temporarytin2026@yahoo.com`
- `SMTP_TIMEOUT=15` (optional; 5–60 seconds)
- `CETTP_TAX_COMPLIANCE_EMAIL=<approved recipient(s)>`
- `CETTP_INVESTMENT_WHT_EMAIL` (optional; falls back to CETTP_TAX_COMPLIANCE_EMAIL)

`SMTP_PASSWORD` must be entered as a Render secret. It is not included in this ZIP. Port 587 uses STARTTLS; port 465 uses implicit TLS.

## Deployment precautions
- Deploy to the existing Render service.
- Preserve the existing `DATABASE_URL`, `SECRET_KEY`, cron token and all other production environment variables.
- Do not reset PostgreSQL or delete existing records.
- The new `portal_email_logs` table is created non-destructively by the existing `db.create_all()` startup call.
- Run the verification checklist in `VERIFICATION_V3_3_0.md` before production use.
