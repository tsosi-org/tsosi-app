# Data preparation

## Raw data

We have 2 input files from PCI to describe all their supports:

- *2025-03-03_PCI_Funding_Report.xlsx* - List of all the received supports where 1 row equals 1 transfer 

- *2025-01-06_PCI_Funding_Data_Identifiers.xlsx* - Additional data to characterize the supporters and intermediaries.


## Entity matching

We check for entities without any entry in the Identifiers file and we look for a ROR or Wikidata ID. If we find one, we add a row to the identifiers file.

We keep track of those extra found IDs in the notebook.


## Processing

We just map the entity data to the transfer data, for both emitters and intermediaries and voilà!
 