# TSOSI Back-end application

TSOSI back-end serves the following purposes:

* Database manager - The database is defined, synchronized and updated using Django ORM. 
* Data workflow - The data pipeline is implemented here.
* API service - Various REST API endpoints are exposed to serve the TSOSI data.

## Overview

* `api` - It contains the definition of the API endpoints. The API is generated using [Django Rest Framework](https://www.django-rest-framework.org/).

* `management` - It contains commands that can be runned from a terminal with django base CLI tool `manage.py`.

* `migrations` - It contains all the migration files used to synchronize the database. They are usually automatically generated.

* `models` - It contains the declaration of all the database models, using Django ORM.

* `data` - It contains all the application logic to prepare, ingest, update and enrich the transferts data.


## Data 

The data repository is organized in files corresponding to the different stages of our workflow.

### [Data preparation](data/data_preparation.py)

This contains the logic to prepare any input data to be ingested in our database.

* A `RawDataConfig` object must be created for each different data source to indicate the source type (file, API), and the mapping of the data source fields to our database schema.

* The main function, `prepare_data`, takes as argument a config and process the associated data accordingly.

* Various checks are made and errors will be raised if the provided data does not suit our standard. For example, the following cases should raise an error/warning:

    * No date value (at least one date is mandatory).
    * An amount is provided without a currency.
    * The provided currency does not fit our sublist of supported currencies (in [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) format).
    * The provided country cannot be mapped to an actual country using pycountries.
    * ...

The output of this preparation is ready to be ingested in our database.

### [Data ingestion](data/ingestion.py)

This contains the code to ingest a prepared dataset of transferts.

* The ingestion process tries to match the given entities with existing ones, using their name, country and PIDs.

* It will then create the new entities, the transferts, the provided identifiers and all the matching data.

* Everything is encapsulated in the function ̀`ingest_new_records`.

### [Data enrichment](data/enrichment.py)

This contains the code to enrich the Entity table with external sources.

* Fetching of external PID records (ROR, Wikidata).
* Fetching of wikipedia extract and wikidata logo files.
* Processing of the above data.
* The record specific code is located in the `pid_registry` folder.


### [Merging](data/merging.py)

This file is dedicated to the task of merging similar entities.


### [Currencies](data/currencies/currency_rates.py)

This contains the code to fetch the rates of the supported currencies and to convert the transfert amounts in those currencies.

* We rely on the [BIS data portal](https://data.bis.org) to fetch the historical currency rates 

* We only fetch the rates for the timeline spanned by the transferts in the database and for the distinct currencies present in the transfert table.   