# Investment WHT Credits – CETTP

Open the module from Tax Compliance Workspace → Investment WHT Credits.

## Batch upload
1. Select **Download batch template**.
2. Complete the required bank, TIN, principal, nature, commencement date, maturity date and annual rate fields.
3. Enter actual WHT already recorded, if any.
4. Optionally enter **Confirmed Expected Interest (Optional)** where the bank's investment advice confirms a different expected interest amount. This overrides the calculated interest for WHT computation while the calculated amount remains stored for comparison.
5. Upload the completed `.xlsx` workbook.

The expected interest calculation is:

`Principal × Annual Rate (%) × Actual Investment Days ÷ 365`

Expected WHT is 10% of the calculated or bank-confirmed expected interest. The template's **Expected WHT (10%)** column is retained to match the register format; CETTP recalculates this amount rather than trusting an uploaded formula/value.

## Reconciliation
After maturity, enter the actual WHT deducted/remitted by the bank, certificate reference and date, and attach the TRA WHT certificate. Outstanding WHT receivable is the positive difference between expected WHT and actual WHT; it cannot become negative.

## Email reminders
The application sends three event reminders when its secured reminder endpoint is invoked daily by the configured scheduler:
- 5 days before maturity;
- on the maturity date;
- on the 8th day of the month following maturity, after the 7th-day WHT filing deadline, to verify the TRA WHT certificate.

See `CHANGELOG_V3_1_0_INVESTMENT_WHT_CREDITS.md` for the environment variables and daily Render Cron Job configuration. SMTP credentials and the cron token must be configured by an authorized administrator; they must never be committed to GitHub.
