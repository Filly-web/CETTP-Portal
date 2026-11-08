# CETTP V2.9 – Fixed Asset Governance integration

## Integration approach
- Adds Fixed Asset Governance as a first-class Flask Blueprint at `/fixed-assets`.
- Reuses CETTP's existing Flask application, SQLAlchemy instance, CSRF protection, session and `DATABASE_URL`.
- Adds new `fa_*` tables only; existing CETTP case, reconciliation, EFD and tax-calendar tables are not renamed or modified.
- Adds a Fixed Asset entry card to the portal landing page and navigation links in the Tax Compliance workspace.
- Retains the V2.8 email recipient configuration and V2.7.1 EFD batch-processing correction.

## Included functional foundation
- Executive fixed asset dashboard and paginated/searchable Master FAR.
- Individual asset creation and category-based asset number generation.
- Excel/CSV staged FAR import, automatic header mapping, manual column mapping, preview and validation.
- Duplicate asset/tag/serial detection, financial equation checks, exception/warning staging and 100,000-row import limit.
- Monthly straight-line, reducing-balance and units-of-production depreciation posting, with unique period control and asset-level history.
- Trial Balance import, configurable category-to-GL mapping and category-level cost/accumulated depreciation/NBV reconciliation.
- First-run period FAR snapshots so repeated reconciliations use the same FAR basis; reconciliation runs are retained as history.
- Variance investigation and resolution notes.
- Asset transfer and disposal transactions, with gain/loss on disposal.
- CWIP projects, expenditure capture and capitalization into an asset.
- Physical verification history and QR image generation.
- Insurance register with renewal/expiry status.
- Tax WDV and indicative deferred-tax schedules.
- Period lock/reopen controls and fixed asset audit log.
- Master FAR exports in XLSX, CSV and PDF; 12-sheet audit pack workbook.

## Important control notes / current release limits
- The existing CETTP Tax Compliance role gate is reused for this initial integration. This is not a new named-user identity provider or a complete enterprise RBAC administration screen. Production rollout requires approved named-user authentication, least-privilege roles and separation of duties.
- Asset additions, transfers and disposals in this foundation are recorded directly by an authorized Tax Compliance session. A maker-checker approval queue and immutable accounting journal posting are still required before production financial close.
- Depreciation starts in the month after the placed-in-service month. Configure `FA_FY_START_MONTH` (1–12; default 1) to align YTD depreciation reset with the organization's financial year. Confirm the policy before posting a live run.
- Straight-line, reducing-balance and units-of-production monthly calculations are supported. Units-of-production requires a total expected units basis and captured period usage; assets without those inputs are skipped, never silently substituted.
- Reducing-balance rate is stored as an annual percentage and divided by 12 for monthly processing.
- The first FAR-vs-TB reconciliation for a period captures a period snapshot. Reconciliation for an old period before a snapshot exists cannot reconstruct historic FAR balances from the current register; load/establish the opening historical register carefully before first reconciliation.
- TB accumulated depreciation is treated as a credit balance and converted to an absolute value for comparison. Validate sign conventions against the organization's chart of accounts.
- Tax WDV is input from the approved capital allowance computation. The schedule calculates temporary differences and indicative deferred tax; it does not determine statutory tax classes/rates or IAS 12 recognition by itself.
- Documents are represented in the data model, but a full upload/download and retention workflow is not yet exposed in the UI. Approval workflows, impairment, component accounting, automated journal export, full IFRS rollforwards and complete audit pack evidence controls remain follow-on work.
- `db.create_all()` creates the new namespaced tables on startup. It does not alter existing CETTP tables. Back up the production database before the first deployment.

## New configuration
- `FA_FY_START_MONTH=1` – first month of the financial year.
- `TAX_ACCESS_CODE` – continue to configure the existing CETTP Tax Compliance access code securely.
- `SECRET_KEY` and `DATABASE_URL` – continue to use the existing CETTP production values.
- `reportlab` is added for PDF register output.
- The pre-existing EFD-to-Invoice utility retains its own local SQLite processing-history/staging store in this release; the new Fixed Asset module and CETTP core business tables share the existing CETTP `DATABASE_URL`. Migrating the EFD utility history store is deliberately separate from this Fixed Asset integration.
