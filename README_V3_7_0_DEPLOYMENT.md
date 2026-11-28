# CETTP V3.7.0 Deployment

Deploy this release over the existing CETTP application using the current Render service and PostgreSQL database. Preserve the existing `DATABASE_URL`, `SECRET_KEY`, SMTP and other environment variables. No database reset or schema migration is required for this release.

After deployment, test as an Initiator:
1. Open New EFD Request and confirm both Digital Invoice and Upload Manual Invoice options appear.
2. Create a digital invoice, select 0% and 18% in separate test requests, preview, and submit.
3. Upload a valid `.docx` manual invoice and confirm the request appears in My EFD Requests and the Tax Compliance Workplace.
4. Confirm a non-Word file and a file exceeding 15 MB are rejected.
5. As Tax Compliance, verify that both request types can be opened, returned, rejected and completed using the existing workflow, and that the processed Word document can be downloaded by the Initiator.

Live Render, PostgreSQL, email-delivery and end-to-end browser testing must be completed in the deployment environment.
