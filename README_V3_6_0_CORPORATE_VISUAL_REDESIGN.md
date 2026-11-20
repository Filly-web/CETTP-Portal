# Britam CETTP V3.6.0 — Corporate Visual Redesign

This release applies a consistent corporate visual design across the CETTP landing page, access screens, shared application shell, role-aware navigation, dashboards and internal page components. The standalone EFD Invoice Portal has also been visually aligned.

## Deployment
1. Back up the currently deployed source and database before deployment.
2. Replace the application source with this release package.
3. Retain the existing Render environment variables, PostgreSQL database URL, start command, cron configuration and persistent service settings.
4. Do not create a new database or run destructive database reset commands. No schema migration is required for this release.
5. Deploy and verify the login routes, initiator and tax workspaces, VAT/WHT tools, EFD request workflow and standalone EFD portal.

## Access behavior
- Initiator remains email-only pilot access; this release does not add email ownership verification or password authentication.
- Tax Compliance continues to use the existing security-code check.
- EFD Invoice Portal continues to use its existing access route and behavior.

## Release contents
See `CHANGELOG_V3_6_0_CORPORATE_VISUAL_REDESIGN.md` for scope and validation boundaries.
