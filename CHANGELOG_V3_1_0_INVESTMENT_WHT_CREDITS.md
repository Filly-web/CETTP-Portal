# CETTP V3.1.0 – Investment WHT Credits

## Added
- Investment WHT Credits module within the existing Tax Compliance Workspace, including dashboard card and Tax Compliance sidebar navigation.
- Individual investment registration and Excel batch upload using the bank investment register fields supplied by Tax Compliance.
- Downloadable blank Excel batch template and full register export.
- Expected interest calculation: principal × annual rate × actual investment days ÷ 365, rounded to two decimal places.
- Optional bank-confirmed expected-interest override; expected WHT recalculates at the fixed 10% rate using the confirmed amount when supplied.
- Actual WHT reconciliation, outstanding WHT receivable calculation, certificate reference/date and PDF/JPG/PNG certificate attachment.
- Exact duplicate detection by bank TIN, principal, investment nature and investment dates.
- Reminder events: five days before maturity, on maturity date, and on the eighth day of the month following maturity to check the TRA WHT certificate after the seventh-day filing deadline.
- Email delivery through the existing Microsoft 365 SMTP integration pattern, with separate recipient configuration and duplicate event suppression.

## Deployment notes
- The module adds new SQLAlchemy tables and does not alter or delete existing CETTP tables or records. Existing `DATABASE_URL`, `SECRET_KEY`, and Render service settings must be retained.
- `db.create_all()` creates the new tables on application startup in this codebase. For environments that use Flask-Migrate migrations operationally, generate and review a migration for the three new tables before deployment.
- Configure `CETTP_INVESTMENT_WHT_EMAIL` with approved recipient email address(es), separated by commas or semicolons. If omitted, the existing `CETTP_TAX_COMPLIANCE_EMAIL` recipient setting is used.
- Email delivery uses `M365_SMTP_HOST`, `M365_SMTP_PORT`, `M365_SMTP_USERNAME`, `M365_SMTP_PASSWORD`, and `M365_SMTP_FROM` already used by CETTP. No credentials are embedded in source code.
- Configure a strong `INVESTMENT_WHT_CRON_TOKEN` environment variable.
- Create a daily Render Cron Job (or approved equivalent) to POST to `/tax-investment-wht/reminders/run` with header `X-CETTP-CRON-TOKEN: <same token>`. Example command:

  ```sh
  curl --fail --silent --show-error -X POST "$CETTP_BASE_URL/tax-investment-wht/reminders/run" -H "X-CETTP-CRON-TOKEN: $INVESTMENT_WHT_CRON_TOKEN"
  ```

- The module evaluates maturity dates using the Africa/Dar_es_Salaam timezone. Run the daily cron in Tanzania time (Africa/Dar_es_Salaam), preferably after midnight and before the business day. If the scheduler is UTC-only, select a UTC time that falls after midnight Tanzania time.
- Reminder endpoint returns counts and records sent/failed/not-configured email events. Sent events are de-duplicated by investment, event type and event date.

## Important calculation and control notes
- Actual investment days are `(maturity date - commencement date).days`; commencement date is excluded and maturity date is the end date. A 365-day denominator is used even in leap years, as instructed.
- The WHT rate is fixed at 10% in this module. It is not a substitute for reviewing applicable tax law or the bank's actual withholding statement.
- The system does not automatically verify bank remittance with TRA. Tax Compliance must record actual WHT and attach/verify the TRA certificate.
- The optional confirmed-interest override is stored separately; the automatically calculated interest remains visible in the export for comparison.
