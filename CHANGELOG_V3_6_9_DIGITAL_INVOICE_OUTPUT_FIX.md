# CETTP V3.6.9 – Digital Tax Invoice Output Fix

## Changes
- Right-align all generated premium, net amount, VAT and gross premium figures within the invoice amount column.
- Set generated financial figures to black text so the red demonstration formatting does not carry into completed invoices.
- Capture `Prepared By` from the authenticated CETTP user's full name (`session.actor_name`) on the server; the form now displays the identity as read-only.
- Replace the manager approval `CAPTURE DATE` placeholder with the generated invoice date.
- Retain automatic preparation date capture and the existing manager name field.

## Compatibility and deployment
- Built on CETTP V3.6.8 Digital Tax Invoice Generator.
- No database schema changes or production data deletion are included.
- Preserve existing Render environment variables and PostgreSQL database.
- Deploy to staging and verify with both 0% and 18% VAT before production deployment.
