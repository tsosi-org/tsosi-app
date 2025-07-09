# Data preparation


## Raw data

We dispose of the following data files:

- *2024-09-20-DOAJ_Library_Report_2021-2023_raw.xlsx*

    All the library supports for the years 2021, 2022 and 2023.

    * Each row corresponds to an actual transfer.

    * For the years 2021 and 2022, transfers made through an intermediary (usually a library consortium) are not individually listed and only the total support made through this intermediary is reported.


- *2025-01-15-DOAJ_Library_Report_2024_raw.xlsx*

    All the library supports for the year 2024. This is an extract from their CRM that they started using for support tracking in 2023 or 2024.

    * 
        Each row with a non-null amount corresponds to an actual transfer. Lines with no amount generally correspond to a past transfer which contributes to this year's budget. 
    
        Ex: Given an upfront transfer in 2022 for 3 years that support DOAJ for 2022, 2023 and 2024, it can be listed in the 2024 library report with no amount.


- *2025-04-29_DOAJ_Library_2024_Invoice_data_review.xlsx*

    Corrective data file for the 2024 Library report one, to be used to remove duplicated transfers.
    
    * This is an extract of transfers listed in the 2024 library report with an invoice date prior to 2023-12-01 so that they're potentially already included in the previous library reports.

    * This contains a boolean column to indicate whether the transfer is a duplicate of an already registered one.


- *2025-04-30_DOAJ_Couperin_2023_breakdown_raw.xlsx*

    The report from COUPERIN of all supports they organized for the DOAJ in 2023.

    * There has been an issue with COUPERIN and part of the supports collected in 2023 were only transfered to the DOAJ in early 2025.

    * This is indicated in the file in the column "Paid Y/N".  


- *2025-04-29_DOAJ_Couperin_2024_breakdown_raw.xlsx*

    The report from COUPERIN of all supports they organized in 2024.



- *2025-01-07-DOAJ_Publisher_Report_2021-2024_raw.xlsx*

    All the "publisher" supports for the years 2021, 2022, 2023 and 2024.

    * Each row corresponds to an actual transfer.



## Processing

The various processing steps are clearly defined in the notebook:


### 1 Pre-processing

Pre-processing of the Couperin specific data to fill the correct `date_payment_recipient` and `date_payment_emitter` dates. 

As of 2025-07-08, this is the only time we have had a time difference big enough to report (2 years between payment and reception).

### 2. 3. & 4. Entity matching/enrichment

We prepare the manual matching for all data files, then manually review it and finally process it.
This follows our base entity enrichment workflow.

### Clean COUPERIN data

For the years 2023 and 2024, we remove the COUPERIN data from the base data files and replace it with the specific exports from COUPERIN.

### Remove flagged duplicates 

Additionally, for the 2024 library report we remove the duplicated transfers indicated in the file *2025-04-29_DOAJ_Library_2024_Invoice_data_review.xlsx*

