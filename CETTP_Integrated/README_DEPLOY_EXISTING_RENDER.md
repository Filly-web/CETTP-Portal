# CETTP – Initiator submission fix (existing Render service)

This package is arranged with the application files at the ZIP root. In particular, `requirements.txt` contains **only pip package requirements**. Do not copy the text of this README or any changelog into `requirements.txt`.

## Deploy to the existing Render service

1. Back up the current production database before deploying.
2. Extract this ZIP. The files `app.py`, `requirements.txt`, `Procfile`, `runtime.txt`, `templates/` and `static/` should be directly inside the repository root (not inside another nested `CETTP_Integrated/` directory).
3. Update the existing GitHub repository with these files. Do not create a new Render service or a new database.
4. In the existing Render Web Service, keep the current database attachment and environment variables unchanged. In particular, do not change `DATABASE_URL` or `SECRET_KEY`.
5. Confirm the existing service's Root Directory is blank (repository root). Use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
6. Deploy the existing service. Check `/health` and review Render Logs after deployment.
7. Sign in as an Initiator, create one test request with the mandatory cancelled invoice/EFD attachment, and confirm that it appears in the Tax Compliance Case Register and Notifications.

## What this release addresses

- Initiator email is used as the Initiator username; no OTP or password is requested for Initiator entry.
- Initiator name is taken from the login email and is not required as an editable form field.
- Form validation errors are displayed and written to the application log rather than silently redisplaying the form.
- Case, attachment, audit entry and Tax Compliance in-app notification are committed in one database transaction. On a database error, the transaction is rolled back and the exception is logged.
- Tax Compliance login controls are unchanged.
- Existing `DATABASE_URL` configuration is unchanged. No database or Render service is defined in this package.

## Requirements file

`requirements.txt` is a plain UTF-8 list of Python dependencies, one per line. Keep explanatory notes, README text and changelogs out of this file.

## Important

The Initiator email-only login does not verify ownership of the email address. Use it only within a controlled pilot environment. A successful code build does not by itself prove that the production database is reachable; verify one test submission in the deployed service.
