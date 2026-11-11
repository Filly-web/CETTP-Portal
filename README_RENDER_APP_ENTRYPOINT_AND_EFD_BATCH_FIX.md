# CETTP V3.0.2 — Render entry-point and EFD batch navigation fix

## Corrections

1. Restores the valid Flask application source in repository-root `app.py`. `app.py` must contain Python code, not Jinja/HTML template content.
2. Restores visible access to the existing EFD batch-processing feature from the EFD Portal dashboard: a sidebar link and a Quick links entry.
3. Retains the existing batch workflow: upload one `.docx` invoice per submission, enter its TRA verification code and receipt time, review/remove staged invoices, then process the staged invoices and download one ZIP package.
4. Retains the V3.0.1 VAT Control Account and other CETTP modules.

## Render deployment

Keep `app.py`, `efd_portal.py`, `requirements.txt`, `Procfile`, `templates/`, and `static/` at the repository root. The included Procfile is `web: gunicorn app:app`. Deploy to the same repository/branch connected to the existing Render service. Do not recreate the service or change `DATABASE_URL`, `SECRET_KEY`, or the database.

## Verification scope

All Python files passed static syntax parsing; the root application entry point, batch route, dashboard links, required templates, requirements file, and ZIP integrity were checked. This is not a live Render deployment test.
