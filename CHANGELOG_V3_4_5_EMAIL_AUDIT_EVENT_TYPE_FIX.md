# Changelog — CETTP V3.4.5

- Fixed central email audit insertion by populating the required `event_type` field.
- Added `event_type` to the email audit model and additive PostgreSQL startup migration.
- Added an idempotent SQL repair script.
- No intentional changes to other CETTP workflows or data.
