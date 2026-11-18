# WHT TIN Matching – V3.4.3

Deploy this release over the existing CETTP application. New features:
1. Upload a WHT ledger workbook by return month.
2. Delete a ledger upload batch and its ledger rows.
3. Review TIN master import history and delete an import batch. Only TIN records created by that batch and still linked to it are removed; existing records updated by the import are preserved.
4. Add one TIN directly from the portal.
5. Select multiple exception rows, allocate a TIN separately to each row, and approve all selected rows together.

The release uses additive startup migrations and does not reset the production database. Python syntax and ZIP integrity checks are performed; full Flask/PostgreSQL/Render integration testing remains pending.
