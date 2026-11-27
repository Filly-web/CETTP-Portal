# CETTP V3.8.1 Deployment – Monthly EFD Compliance

1. Back up the existing PostgreSQL database before deployment.
2. Deploy this source package to the existing Render web service using the current repository and build/start commands.
3. Preserve the existing `DATABASE_URL`, `SECRET_KEY`, SMTP variables and all other production environment variables. Do not create a new database or reset the existing one.
4. The existing startup `db.create_all()` call creates the additive `efd_recon_batches` and `efd_recon_rows` tables. It does not drop or rewrite existing application tables.
5. Sign in as Tax Compliance or CETTP Admin and open **EFD Compliance Check**.
6. Select the reporting month, upload the AIMS report and upload the corresponding TRA report. The application reads AIMS `TaxEfdCode` and TRA `RCTVNUM` by header name.
7. Review both directions of unmatched verification codes, duplicate codes, missing-code records, cancellation exceptions and Bankassurance follow-up. Download the Excel exception report for workpapers.
8. CETTP Admin can replace or delete a monthly source batch. Superseded versions remain visible in the selected month's upload history. Only CETTP Admin can permanently delete EFD requests, including processed requests.
9. Verify the existing VAT reconciliation, WHT, cancellation/endorsement and EFD request workflows after deployment.

## Important
- The TRA sample provided has `Z#` in column F and `RCTVNUM` (verification code) in column G. The parser uses the `RCTVNUM` header, not a fixed column position.
- The monthly report comparison is a verification-code reconciliation, not proof that an EFD cancellation/adjustment was accepted by TRA.
- Bankassurance exceptions require manual confirmation against the integrated bank EFD machine and TRA records; no external bank or TRA API is connected.
- Test the release in a staging environment before production deployment. This build has not been connected to or tested against the live Render PostgreSQL database, live email service, TRA or bank systems.
