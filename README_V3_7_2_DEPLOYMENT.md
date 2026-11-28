# CETTP V3.7.2 Deployment

1. Back up the current source and confirm the existing Render PostgreSQL database is attached.
2. Replace the V3.7.1 application source with this release package.
3. Keep existing Render environment variables, including `DATABASE_URL`, `SECRET_KEY`, and SMTP settings. Do not create a new database or reset production data.
4. Deploy and test in staging before production use.

## Staging test checklist
- Generate digital invoices using both 0% and 18% VAT.
- Confirm the customer address and Customer ID have no unnecessary gap.
- Confirm the invoice and final processed invoice each remain on one page for normal invoice descriptions (maximum 300 characters).
- Confirm the Tax Compliance user can complete a digital invoice by entering the actual TRA verification code and receipt time without uploading a processed Word file.
- Confirm the QR code appears in the final Word invoice and the Initiator can download it from CETTP.
- Confirm completion notification is sent to the Initiator.
- Confirm manual invoice requests still require the processed Word file upload and remain downloadable.

## Important QR-code limitation
CETTP generates the QR code using the existing verification URL pattern. It does not obtain or issue the TRA verification code and does not independently validate it with TRA. Tax Compliance must enter the code and receipt time exactly as shown on the TRA receipt.

## Validation performed for this package
- Python syntax compilation for `app.py`, `efd_portal.py`, and `calendar_reminders.py`.
- Jinja parsing for all 37 HTML templates.
- Generated and rendered both 0% and 18% VAT final digital invoices to PDF; both rendered as one page.
- Confirmed the final document includes the entered verification code, receipt time and embedded QR image.
- Full Flask runtime, live PostgreSQL, Render deployment, SMTP delivery and live TRA verification were not tested in this build environment.
