# CETTP enhancement: overdue monitoring, reconciliation review and compact UI

- Added configurable overdue monitoring to the Tax Compliance dashboard. Open cases at or beyond `CETTP_OVERDUE_DAYS` are listed oldest-first; default threshold is 5 days. Closed cases are excluded.
- Added Premium Register reconciliation summary cards for exact amount matches, different amount review cases, pure cancellations, and rows not yet linked to a CETTP case.
- Clarified that policy/amount matching is a review suggestion and should be checked against dates, document numbers and existing cases before import.
- Reduced general typography and button sizing for a more compact, professional interface while retaining responsive layouts.
- No WHT reconciliation module added.

## Configuration
Optional Render environment variable: `CETTP_OVERDUE_DAYS=5`. Change the value to the agreed internal follow-up threshold.

## Deployment note
Deploy to the existing service only after backing up the production database and merging the package changes into the currently connected source. Review any existing custom CSS/template changes before replacing files.
