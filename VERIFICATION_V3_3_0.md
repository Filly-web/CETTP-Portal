# V3.3.0 Verification Checklist

1. Install dependencies from `requirements.txt`.
2. Run `python -m py_compile app.py efd_portal.py`.
3. Compile every Jinja template with Flask/Jinja (`app.jinja_env.get_template(name)`).
4. Confirm `templates/cancellation_tracker.html` has one `scripts` block.
5. In a staging database, test manual investment edit, individual delete, batch delete and confirm manual/other-batch rows remain.
6. Test cancellation filter, classification correction, page selection, Previous/Next and classification import; confirm imported rows are not imported twice.
7. Configure Yahoo SMTP secrets in Render and test email delivery. A timeout on Render Free may still indicate outbound SMTP network restrictions; the application now records the exception in the central log and does not interrupt case submission.
8. Confirm case notifications and Investment WHT reminders appear in the central email log.
9. Deploy to the existing Render service without changing `DATABASE_URL` or resetting the database.
