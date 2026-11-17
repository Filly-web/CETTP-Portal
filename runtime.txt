# EFD template fix — deployment notes

The EFD portal's templates are explicitly namespaced to prevent collisions with CETTP templates of the same name.

- Dashboard: `templates/efd_portal/index.html`
- Processing history: `templates/efd_portal/history.html`

Render settings (assuming `app.py` defines `app` at repository root):
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Do not change the existing database URL or create a new service for this fix. Back up existing databases before replacing files. After deployment, test Initiator login, Tax Compliance login, EFD invoice generation, EFD history, and Back to CETTP navigation.
