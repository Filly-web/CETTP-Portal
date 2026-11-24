# V3.8.0 Deployment – VAT Reconciliation

1. Back up the existing PostgreSQL database before deployment.
2. Replace the application source with the V3.8.0 package and deploy using the existing Render service configuration.
3. Retain the existing `DATABASE_URL`, `SECRET_KEY`, SMTP settings and all other environment variables.
4. On startup, the existing `db.create_all()` call creates the two new VAT reconciliation tables. Existing tables and records are not dropped or reset.
5. Open **VAT Reconciliation** from the Tax & Reconciliation sidebar.
6. Download the standard import template and populate it using the actual source data. Import each source separately for the same reporting period.
7. Import AIMS Premium and/or AIMS Commission plus EFDMS to enable reference-level matching. Import GL and VAT return data for separate source totals.
8. Review exceptions and reconcile them to source documents before using any figures for a VAT return.

## Important
The module is an initial transaction-level reconciliation foundation. It does not yet automatically map arbitrary AIMS/GL export formats, reconcile every VAT-return box, calculate legally recoverable input VAT, or submit returns to TRA. Use the standard template until source-specific import mappings are configured and tested. Test in staging before production deployment.
