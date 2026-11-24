# CETTP V3.6.9 Deployment

This is a patch release over V3.6.8. It corrects Word invoice formatting and identity/date population.

1. Back up the current deployment/source and confirm the existing PostgreSQL database remains configured.
2. Deploy this ZIP to a staging service using the existing Render start command and environment variables.
3. Sign in as an Initiator account with a populated Full Name in CETTP user management.
4. Generate sample invoices at 0% and 18% VAT.
5. Confirm all monetary amounts are right-aligned and black, Prepared By matches the signed-in user's full name, and the manager date is populated rather than showing `CAPTURE DATE`.
6. Verify preview, submission, Tax Compliance processing and final Word download before promoting to production.

No database reset or migration is required for this patch.
