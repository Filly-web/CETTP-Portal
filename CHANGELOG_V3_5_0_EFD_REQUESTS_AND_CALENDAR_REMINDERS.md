# CETTP V3.5.0 — EFD Invoice Requests and Tax Calendar Reminders

## EFD Invoice Request workflow
- Initiators can submit a Word invoice request from the existing initiator portal.
- Supplier name, purpose, and Word invoice attachment are mandatory; TIN, invoice number/date, amount and currency are optional.
- Requests have unique references and are stored with original attachment.
- Tax Compliance receives an email on request submission.
- Admin queue lists requests and supports review/detail.
- Detail page offers an extracted text preview of the Word invoice plus original document viewing.
- Tax Compliance records EFD verification code, receipt time, and uploads processed Word invoice.
- Request is marked completed and initiator receives an email notification.
- Initiators can only access requests submitted under their email address.
- Requester can download processed invoice from own request history.

## Calendar reminders
- `calendar_reminders.py` is the daily runner for Render Cron.
- Sends daily reminders to faugusti@britam.co.tz for deadlines 5, 4, 3, 2, 1, or 0 days away.
- Stops sending once a deadline status is Completed or Not Applicable.
- Duplicate reminder sends are prevented by per-deadline, due-date, day-count, and date audit keys.
- The reminder runner uses the central CETTP email sender and audit log.

## Deploy
1. Update application source from the release.
2. Create a Render Cron Job with command `python calendar_reminders.py` and schedule daily at a suitable time (timezone UTC; adjust for Tanzania if needed).
3. Keep SMTP credentials only in Render environment variables.
4. No database reset is required. The `efd_invoice_requests` table is additive and created by the app's existing `db.create_all()` startup.
