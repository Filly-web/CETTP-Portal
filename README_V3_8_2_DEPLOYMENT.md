# CETTP V3.8.2 Deployment Notes

This is an incremental enhancement of V3.8.1. It preserves the existing Flask application, PostgreSQL schema and existing deployment configuration.

## Before deployment
- Take a verified PostgreSQL backup.
- Keep the existing `DATABASE_URL`, `SECRET_KEY`, admin bootstrap, and SMTP environment variables in Render; do not replace them with values from `.env.example`.
- Download/retain the currently deployed release for rollback.

## Deploy
1. Upload/deploy the contents of this ZIP to the existing Render service.
2. Execute `migrations/V3_8_2_efd_compliance_indexes.sql` against PostgreSQL. This only adds indexes with `IF NOT EXISTS`.
3. Restart the existing service.
4. Test sign-in, VAT reconciliation, EFD request processing/email, monthly AIMS/TRA uploads and exports.
5. Confirm Tax Compliance and Admin deletion permissions and Initiator denial using non-production test records first.

## EFD upload notes
- Supported formats: `.xlsx`, `.xlsm`, `.csv`; `.xls` is intentionally rejected because OpenPyXL does not support the legacy binary format.
- Maximum file size is 25 MB.
- Excel parsing is sequential and read-only. The actual monthly AIMS/TRA reports should be tested in staging because no sample workbooks were included in the supplied source archive.
- If measured production processing still exceeds the synchronous Render request window, implement a persistent background worker/queue in a separately provisioned service; this release does not claim that a background worker has been deployed.

## Rollback
Redeploy the previous V3.8.1 source package. The additive index migration can safely remain in place; it does not change application data or existing table definitions.
