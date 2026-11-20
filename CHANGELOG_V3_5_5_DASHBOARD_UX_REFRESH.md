# Britam CETTP V3.5.5 — Dashboard UX Refresh

## Overview
This release refreshes the landing page and role dashboards to reduce explanatory text and make the three workspaces easier to identify and navigate.

## Changes
- Replaced the text-heavy landing page with three concise workspace tiles: Initiator, Tax Compliance and EFD Invoice.
- Simplified sidebar labels and footer version branding.
- Reworked the Initiator dashboard with direct quick actions for EFD invoice requests, existing cases and compact request-status summaries.
- Simplified Tax Compliance dashboard descriptions and added a direct EFD Invoice Requests shortcut.
- Shortened introductory and guidance copy in the EFD Invoice Portal dashboard.
- Added responsive styling for smaller screens while retaining the existing Bootstrap layout and application routes.

## Compatibility and data safety
- Presentation/template/CSS changes only, plus dashboard navigation links.
- No database schema changes or data migrations.
- Existing tax calculations, request workflows, access checks and persistence logic are unchanged.
- This release is based on the supplied V3.5.4 package. It therefore inherits that package's baseline and does not independently add V3.5.3-only features that were absent from V3.5.4.

## Validation
- Python compilation: passed.
- Jinja template parsing: passed for all 30 HTML templates.
- ZIP integrity: checked after packaging.
- Live Render, PostgreSQL and browser visual testing: not performed in this environment.
