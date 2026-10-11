# Data preparation

## Raw data

Episciences (CCSD) sends a single file filled in from the TSOSI data template:

- _2025--TSOSI-data-schema-EPISCIENCES.xlsx_ - All the supports received by Episciences, with 2 sheets:

  - _Par année_ - 1 row = 1 yearly payment. This is the sheet we use (and the one Episciences considers the most accurate).

  - _Transfers_ - 1 row = 1 contract or invoice, with the total amount over the contract period. Not used: dates are in mixed formats (`31.01.2025`, the invalid `2027-31-12`) and it duplicates the yearly rows.

## Processing

- Drop the rows whose intermediary is Couperin (ROR `035c9qf67`). Couperin supports are ingested from Couperin's own data, and the years in the Episciences file don't match them: the rows dated 2025 match Couperin's 2024 campaign.

- Only keep supports actually received: drop the rows without any `date_invoice`, `date_sent` or `date_received` (future instalments of multi-year contracts) and the rows with a date in the future.

- Split the ETH Zürich support (10,500 € received at once in 2025) into 3 transfers of 3,500 € received in 2025, 2026 and 2027 (year precision), as CSAL declares it, so that they merge with the `csal` data source.