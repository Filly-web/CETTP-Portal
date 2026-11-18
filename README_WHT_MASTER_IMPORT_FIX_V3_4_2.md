# V3.4.2 deployment notes

This release addresses worker termination during large Supplier TIN Master imports by streaming CSV/XLSX rows and avoiding a database query for every row. Existing records are prefetched once; writes are flushed in chunks and committed once at the end.

Deploy the package through the existing Render-connected repository. No database reset is required. If the same timeout persists, check Render PostgreSQL availability/connection limits and upload size, and provide the complete traceback preceding the psycopg wait/SystemExit lines.

Validation performed: Python syntax compilation and ZIP integrity only. Live Render/PostgreSQL testing has not been performed.
