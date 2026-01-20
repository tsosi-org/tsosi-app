# Data preparation

## Raw data

We dispose of the following data files:

- _2024-09-20-DOAJ_Library_Report_2021-2023_raw.xlsx_

  All the library supports for the years 2021, 2022 and 2023.
  - Each row corresponds to an actual transfer.

  - For the years 2021 and 2022, transfers made through an intermediary (usually a library consortium) are not individually listed and only the total support made through this intermediary is reported.

- _2025-01-15-DOAJ_Library_Report_2024_raw.xlsx_

  All the library supports for the year 2024. This is an extract from their CRM that they started using for support tracking in 2023 or 2024.
  - Each row with a non-null amount corresponds to an actual transfer. Lines with no amount generally correspond to a past transfer which contributes to this year's budget.

    Ex: Given an upfront transfer in 2022 for 3 years that support DOAJ for 2022, 2023 and 2024, it can be listed in the 2024 library report with no amount.

- _2025-04-29_DOAJ_Library_2024_Invoice_data_review.xlsx_

  Corrective data file for the 2024 Library report one, to be used to remove duplicated transfers.
  - This is an extract of transfers listed in the 2024 library report with an invoice date prior to 2023-12-01 so that they're potentially already included in the previous library reports.

  - This contains a boolean column to indicate whether the transfer is a duplicate of an already registered one.

- _2025-04-30_DOAJ_Couperin_2023_breakdown_raw.xlsx_

  The report from COUPERIN of all supports they organized for the DOAJ in 2023.
  - There has been an issue with COUPERIN and part of the supports collected in 2023 were only transfered to the DOAJ in early 2025.

  - This is indicated in the file in the column "Paid Y/N".

- _2025-04-29_DOAJ_Couperin_2024_breakdown_raw.xlsx_

  The report from COUPERIN of all supports they organized in 2024.

- _2025-01-07-DOAJ_Publisher_Report_2021-2024_raw.xlsx_

  All the "publisher" supports for the years 2021, 2022, 2023 and 2024.
  - Each row corresponds to an actual transfer.

## Processing

The various processing steps are clearly defined in the notebook:

### COUPERIN

Before 2026, we used data from couperin for years 2023 and 2024 to populate doaj files. Now that we ingest data directly from couperin, all couperin data from doaj are removed before ingestion.

### 1 Pre-processing

### 2. 3. & 4. Entity matching/enrichment

We prepare the manual matching for all data files, then manually review it and finally process it.
This follows our base entity enrichment workflow.

### Remove flagged duplicates

Additionally, for the 2024 library report we remove the duplicated transfers indicated in the file _2025-04-29_DOAJ_Library_2024_Invoice_data_review.xlsx_
