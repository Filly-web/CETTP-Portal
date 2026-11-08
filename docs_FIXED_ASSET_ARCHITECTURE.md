# Fixed Asset Governance – Integrated Architecture

## Runtime topology

```text
Browser
  |
  v
CETTP Flask application (single deployment / domain)
  |-- Existing CETTP routes and templates
  |-- Existing EFD-to-Invoice Blueprint
  |-- Existing Tax Compliance Calendar
  |-- Fixed Asset Governance Blueprint (/fixed-assets)
          |-- Asset register and import staging
          |-- Depreciation / disposal / transfer services
          |-- CWIP / verification / insurance / tax schedules
          |-- Trial Balance / GL mapping / reconciliation
          |-- FAR and audit pack exports
  |
  v
Existing SQLAlchemy db instance + existing DATABASE_URL
  |-- Existing CETTP tables (unchanged)
  |-- New fa_* tables (fixed asset domain)
```

## Project structure

```text
calendar_v26/
├── app.py                         # Existing CETTP application and shared db
├── efd_portal.py                  # Existing EFD-to-Invoice Blueprint
├── fixed_assets/
│   ├── __init__.py
│   ├── models.py                  # Namespaced fa_* SQLAlchemy models
│   ├── routes.py                  # Fixed asset services and routes
│   └── templates/fixed_assets/    # Module-specific UI
├── templates/                    # Existing CETTP templates + updated shell
├── static/                       # Existing CETTP assets
├── requirements.txt
├── Procfile
└── docs_FIXED_ASSET_ARCHITECTURE.md
```

## Database boundaries

The fixed asset domain uses `fa_`-prefixed tables to avoid collisions with CETTP's existing `case`, `audit_log`, `reconciliation_item`, `tax_deadline` and EFD tables. It uses the same SQLAlchemy engine and `DATABASE_URL`; it does not create a second PostgreSQL database. Financial amounts use `NUMERIC(20,2)` and rate fields use fixed precision numeric types. Large register pages are paginated and imports are staged before posting.

## Operational lifecycle

1. Stage and validate the legacy FAR.
2. Correct column mapping and resolve hard exceptions; warnings such as missing department/useful life are retained for remediation.
3. Post validated rows into the asset master.
4. Maintain additions, CWIP capitalization, transfers and disposals.
5. Process monthly depreciation once per period.
6. Import period TB and configure category GL mappings.
7. Capture the FAR snapshot and generate reconciliation; investigate and resolve variances.
8. Generate the Master FAR, audit pack and financial period controls.

## Scale and production hardening

The schema uses indexed asset identifiers, category/status, department/location, dates, batch IDs and period/account combinations. The FAR import is capped at 100,000 rows per batch and uses staging. Before production scale-up, load-test representative 100,000+ asset volumes, move long-running imports/depreciation/report generation to background jobs, tune database indexes, add connection pooling, implement backup/PITR and object storage, and run restore/disaster-recovery exercises.

> Database scope: CETTP core and Fixed Asset Governance share the same PostgreSQL `DATABASE_URL`. The existing EFD-to-Invoice utility retains its pre-existing local SQLite history/staging store in this release; it has not been migrated as part of the Fixed Asset module integration.
