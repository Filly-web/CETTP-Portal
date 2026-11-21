# CETTP V3.6.7 — Automated User Access Emails

- Automatically sends user access email after successful account creation by Admin.
- Email includes CETTP portal link, work email, and initial PIN/password.
- Uses role-specific credential labels (Initiator PIN; Tax Compliance/Admin password).
- Account creation is committed independently of email delivery; failed email does not roll back account creation and a warning is shown.
- Credential reset now also emails the newly set credential to the user, enabling a resend/reissue workflow without storing plaintext credentials.
- Central outbound email service and PortalEmailLog are used for delivery/audit status.
- Optional `CETTP_PORTAL_URL` environment variable; defaults to https://cettp-portal.onrender.com/.
- Existing database and records preserved; no database reset.
