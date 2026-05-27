# Data preparation

The processing of DOAB data has been the most tedious due to the very poor quality of their data along with the numerous back and forth to know whether some rows were correct.


## Raw data

As of 2025-07-08, we dispose of three raw data files:

- *2025-02-11-DOAB_Sponsorship_Report.xlsx* - The sponsorship transfers from 2021 to February 2025.

- *2025-02-11-DOAB_Library_Report.xlsx* - Library supports from 2020 (not exhaustive) until 2025 ??. The data is not clear.

- *2025-02-11_DOAB_Library_support_no_amount_reviewed.xlsx* - An additional list of library supports that were reviewed because they had a null amount in the previous file.



## Pre-processing

The data is provided as a breakdown of participation for a given year, which does not reflect the actual transfers behind that, except for the last updated file, *2025-02-11_DOAB_Library_support_no_amount_reviewed.xlsx*, where there's only one line per support as a contract.

The processing consists in:

- Filtering out the rows that are not transfers (no amount )

- Grouping all the rows corresponding to the same transfer. Those are the ones flagged as "Upfront" in the main data file, *2025-02-11-DOAB_Library_Report.xlsx*.

    This is tricky because the rows don't have any ID to reference a support/contract. We group them based on multiple columns and ensure that the number of years in the **Commitment period** corresponds to the number of rows in the group. 

    Note that this should not be performed for the update file *2025-02-11_DOAB_Library_support_no_amount_reviewed.xlsx* because the upfront transfers already correspond to one line there.


- Ensuring the "One Year Commitment" transfers really cover only 1 year

- Check that annual transfers really span 1 year


## Merge back the results

The 2 files *2025-02-11-DOAB_Library_Report.xlsx* and *2025-02-11_DOAB_Library_support_no_amount_reviewed.xlsx* correspond to the same source `doab_library` so we need to group them back together for ingestion due to the data load constraint (only one data load per year per source). 


## PID enrichment

Default PID enrichment of data without PIDs.

The exception is that once the enrichment was done, we re-used it because the "raw" data kept being updated from the DOAB (removal or addition of some rows).
