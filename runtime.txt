# CETTP + EFD-to-Invoice Portal — Render Deployment

## Package layout
This ZIP is intentionally flattened: `app.py`, `efd_portal.py`, `requirements.txt`, `Procfile`, `templates/`, and `static/` are at the ZIP/repository root. Do not leave these files nested inside an extra `CETTP_Integrated/` folder when deploying to the repository root.

## Existing Render service settings
- Root Directory: blank if these files are at the GitHub repository root.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Runtime: Python 3.12 (or a Python version supported by the pinned dependencies).

`gunicorn` is explicitly included in `requirements.txt`. If Render still reports `gunicorn: command not found`, inspect the build log to ensure `pip install -r requirements.txt` ran successfully against this repository root. Do not change the database URL to fix a missing executable.

## Safe deployment
1. Back up the existing CETTP database and any persistent EFD portal history.
2. Update the files in the existing GitHub repository; do not create a new Render service.
3. Keep the existing `DATABASE_URL`, `SECRET_KEY`, and other environment variables unchanged.
4. Deploy the latest commit. If dependency changes do not install, use Render's “Clear build cache & deploy”.
5. Test the home page, Initiator login, Tax Compliance login, creating a case, editing/resubmitting a returned case, and the EFD-to-Invoice page.

## Data persistence
CETTP case data uses `DATABASE_URL` (defaulting to local SQLite only for development). Keep the production `DATABASE_URL` unchanged. The EFD portal stores its processing history in SQLite under `EFD_PORTAL_DATA_DIR` (default: `instance/`). On Render, the default filesystem may be ephemeral. If EFD processing history must persist, configure `EFD_PORTAL_DATA_DIR` to a mounted persistent disk path in the existing service. This is separate from the CETTP database.

## Security
Set a strong, stable `SECRET_KEY` in Render. The email-only Initiator login does not verify ownership of the email address; restrict use to a controlled internal pilot until identity verification is added.
