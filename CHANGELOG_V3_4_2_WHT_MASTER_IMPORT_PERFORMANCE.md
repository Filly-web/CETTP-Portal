# CETTP V3.4.2 – WHT Supplier TIN Master Import Performance Fix

- Replaced eager worksheet loading (`list(...)`) with row streaming for CSV and read-only XLSX/XLSM imports.
- Prefetches existing TIN master records once and uses in-memory indexes to avoid per-row database SELECT queries.
- Flushes ORM pending changes every 500 rows to limit memory use while retaining a single transaction.
- Keeps required-column validation, duplicate agency/TIN conflict checks, and rollback on errors.
- This is an additive application-code fix; it does not drop, reset, or delete production data.
