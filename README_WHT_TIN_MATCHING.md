# WHT TIN Matching – User Guide

1. Open **WHT TIN Matching** from the Tax Compliance navigation.
2. Import/update the Supplier TIN Master. Required headers: `TIN`, `Agency Name` (or `Business Name`); optional: `Sole Proprietor Name`.
3. Prepare one Excel workbook with a separate worksheet for each GL-coded ledger (330301–330318) and each applicable named ledger (Medical Reinsurance Premium, GI Reinsurance Premium, Prior Periods, Smart Brokers, Non-Smart Agencies).
4. Each ledger sheet must contain: `GL Date`, `Natural Account Description`, `Transaction Number`, `Batch Name`, `Supplier/Customer Name`, `Transaction`, `Transaction Description`, `Accounted Amount`, `GROSS-AMOUNT`, `TIN`.
5. Upload the combined workbook once. The portal stores the source values and evaluates Supplier/Customer Name against Agency Name and Sole Proprietor Name.
6. Download the batch report. Check the Summary, Second Review and Unmatched worksheets. Approve reviewed rows in the portal using a TIN from the master.

## Match outcomes
- **80%–100%:** auto-matched only where the candidate TIN is unique.
- **60%–79%:** Second Review; no TIN is auto-approved.
- **Below 60%:** Unmatched.
- **Conflicting/near-equal candidates:** Second Review regardless of the top score.

The report contains a Summary, one output worksheet per imported ledger, Second Review, Unmatched and Supplier TIN Master.
