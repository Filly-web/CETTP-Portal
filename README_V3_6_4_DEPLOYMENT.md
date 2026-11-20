# CETTP V3.6.4 Deployment

1. Back up the current source repository and retain the existing Render PostgreSQL database.
2. Replace the deployed application source with the contents of this ZIP (the ZIP contents are at the project root; do not place the whole extracted project inside another `src` folder).
3. Confirm `app.py` begins with Python imports and that `templates/efd_portal/history.html` remains at that exact path.
4. Keep existing `DATABASE_URL` and `SECRET_KEY` unchanged.
5. Set `CETTP_ADMIN_EMAIL`, `CETTP_ADMIN_NAME`, and `CETTP_ADMIN_PASSWORD` in Render. Use a strong password of at least 12 characters.
6. Deploy. Check startup logs before testing login.

The bootstrap creates the configured Admin if absent. If that exact account exists but is inactive or has a non-admin role, it activates/restores it and applies the environment password once, requiring a password change at next login. An already-active Admin's password is not overwritten on each restart.

This release does not reset or recreate PostgreSQL and does not delete existing user or business records.
