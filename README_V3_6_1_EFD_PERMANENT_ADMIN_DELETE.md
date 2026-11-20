# CETTP V3.6.1 — EFD Permanent Admin Deletion

This release changes Tax Compliance EFD-request deletion to a permanent purge. The admin action deletes the EFD request row, embedded original/processed document data, request audit rows, and associated central email-log rows for the EFD request module. It no longer creates a deletion audit record.

Return, Reject and Amendment workflows are preserved. The action remains Tax Compliance-role restricted and requires browser confirmation with an irreversible-action warning.

Deploy over the existing source without resetting or recreating PostgreSQL. Test deletion with a disposable request after deployment. App-level deletion does not erase infrastructure backups or external logs.
