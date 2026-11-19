# V3.5.2 — Central Email Audit Resilience

## Fix
- Decoupled SMTP delivery from central email audit persistence. A failure to insert an audit row no longer prevents the application from attempting delivery.
- Central email delivery reports success only after the SMTP server accepts the message through `send_message`.
- Audit persistence remains best-effort and records detailed exceptions in Render application logs.
- Expanded the startup migration for `portal_email_logs` to add missing legacy-compatible columns using additive ALTER TABLE operations and populate safe values for legacy rows.
- No tables are dropped, truncated, or recreated; existing records are preserved.

## Deployment
Deploy this source package to the existing Render service. Review startup logs for `Portal email log schema compatibility check completed` and any migration errors. Then test a new request and verify actual receipt at `faugusti@britam.co.tz`. Also test completion notification to the requester's login email.

## Validation boundary
Python syntax compilation and ZIP integrity were checked locally. Live PostgreSQL migration, Render deployment, SMTP connectivity, and real email delivery have not been tested in this environment.
