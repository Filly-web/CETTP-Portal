# V2.9.1 — Cancellation Tracker batch deletion fix

- Changed batch deletion order to remove the batch's `CancellationTrack` rows before deleting any Premium Register-imported `Case` records.
- Preserves Initiator-created cases, including cases linked to a tracker row.
- Wrapped deletion in a transaction with rollback and server-side exception logging.
- No schema migration or database URL change.

Validation: Python syntax compilation and ZIP integrity check. A live Render/PostgreSQL test was not performed.
