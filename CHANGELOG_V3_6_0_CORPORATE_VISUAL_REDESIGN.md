# CETTP V3.6.0 — Corporate Visual Redesign

## Scope
- Redesigned the portal entry page and role access screens with a corporate split-panel layout.
- Rebuilt the shared application shell with a consistent header, role-aware navigation, grouped menu sections, user identity, notification indicator and page context.
- Applied a unified corporate design system to forms, tables, cards, alerts, buttons, modals, pagination and responsive layouts.
- Updated the standalone EFD Invoice Portal palette to align with the main CETTP visual identity.
- Preserved existing routes, role checks, form field names, CSRF behavior, workflow logic and database configuration.

## Baseline consolidation
- Started from V3.5.5 (which includes V3.5.4 EFD request return/reject/soft-delete controls).
- Restored the V3.5.3 VAT ERP import batch deletion route and its Tax Compliance-only UI action, which V3.5.5 had omitted.
- Retained the V3.5.3 optional EFD verification code and receipt time behavior already present in V3.5.5.

## Data safety
- No database schema changes or migrations introduced.
- No production database connection string, credentials or Render settings changed.
- No production records are deleted by this visual release. The restored VAT batch deletion action remains an existing explicit user-triggered feature and continues to preserve manual VAT movements and TRA return records.

## Validation boundary
- Python compilation, Jinja template parsing and ZIP integrity are checked for this package.
- No live Render deployment, production PostgreSQL test, SMTP test or browser end-to-end test is claimed.
