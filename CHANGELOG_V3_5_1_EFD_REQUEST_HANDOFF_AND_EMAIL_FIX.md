# V3.5.1 — EFD Request Handoff and Email Notification Corrections

## Changes
- Initiator request form now requires only Customer Name and a Word invoice upload (.doc/.docx).
- Request alert is sent to faugusti@britam.co.tz through the central SMTP/email audit service.
- Email send result is checked and surfaced to the user; failed delivery is not reported as successful.
- Completion email is sent to the initiator login email address and its result is surfaced.
- Tax Compliance can retry the relevant notification from the request detail page.
- Tax Compliance request detail links directly to the existing EFD to Invoice Portal with the originating request context.
- EFD portal displays a return-to-request link when opened from a request.
- Existing data tables and portal databases are retained; changes are additive.

## Deployment
1. Deploy the full source ZIP without resetting or dropping the production database.
2. Confirm Render environment variables: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_TIMEOUT, SMTP_STARTTLS. For Yahoo SMTP use smtp.mail.yahoo.com, port 587, STARTTLS enabled, and a Yahoo app password.
3. Ensure the hosting plan/network permits outbound SMTP. Render Free services may block SMTP; code changes cannot override provider-level network restrictions.
4. Test a real request and completion using a live initiator account, then verify the email audit log.

## Verification limits
Python syntax compilation and ZIP integrity are checked for this package. Live PostgreSQL, browser workflow, Yahoo SMTP delivery and Render deployment are not tested in this build environment.
