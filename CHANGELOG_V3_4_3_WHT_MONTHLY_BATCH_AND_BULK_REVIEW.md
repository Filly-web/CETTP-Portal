# CETTP V3.4.3 – WHT TIN Matching Workflow Improvements

- Added reporting month field to each WHT ledger workbook upload (YYYY-MM).
- Added deletion of individual ledger upload batches with cascading ledger-row removal.
- Added TIN Master import history and batch deletion; records newly created by a deleted batch are removed only when they still reference that originating batch. Existing master records updated by the import are preserved.
- Added manual single-TIN entry without an upload.
- Added bulk review allocation: select multiple ledger rows, choose a TIN per row, and approve selected allocations in one submission.
- Added additive startup migration for the ledger period and TIN-master import provenance columns; no existing data is reset.
