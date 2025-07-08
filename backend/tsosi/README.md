TSOSI back-end serves the following purposes:

* Database manager - The database is defined, synchronized and updated using Django ORM. 
* API service - Various REST API endpoints are exposed to serve the TSOSI data, mainly to the frontend application.
* Data workflow - The data pipeline is implemented here.

# Overview

* `api` - It contains the definition of the API endpoints. The API is generated using [Django Rest Framework](https://www.django-rest-framework.org/).

* `management` - It contains commands that can be runned from a terminal with django base CLI tool `manage.py`.

* `migrations` - It contains all the migration files used to synchronize the database. They are usually automatically generated.

* `models` - It contains the declaration of all the database models, using Django ORM.

* `data` - It contains all the application logic to prepare, ingest, update and enrich the transfers data.


--- 

The rest of this document provides additional information about the `data` directory. The other ones are very straightforward for a Django user.

The data directory is organized in sub-directories corresponding to the different stages of our workflow.

# [Data preparation](./data/preparation/)

This contains the code to prepare any input data to be ingested in our database.

We use dedicated python notebooks per infrastructure or per dataset type.
The data preparation is currently only performed locally.

The following diagram summarizes the preparation process:


```mermaid
flowchart LR
    A("Get raw data")
    B("Infra-dependent processing")
    C("Enrich entities with PIDs")
    D("Create \`RawDataConfig\`")
    E("Generate TSOSI data file")

    A e1@==> B
    B e2@==> C
    C e3@==> D
    D e4@==> E

    classDef animate stroke-dasharray: 9\,5,stroke-dashoffset: 900,animation: dash 25s linear infinite;
    class e1,e2,e3,e4,e5 animate;
```


## Raw data source

All our partners provide data in the form of .xlsx spreadsheets except for SciPost where we use a dedicated API with private credentials, see `get_scipost_raw_data` in [get_data.py](./data/preparation/scipost/get_data.py).

All the data files at different stage are stored on the UGA cloud, with private access.


## Infra-dependent processing

We have a custom data processing for each of our partners, and sometimes multiple different processing per partner when the data format changes throughout the years.

This processing includes:

- The `selection` or `filtering` of the actual transfers according to specific criterias implemented with the partner's insights.

- The `reshaping` of the transfer data, e.g., for the DOAB where the data comes as the amount of support per year when we want the distinct individual transfers.

- Some little processing to match our available inputs, see more in `RawDataConfig` below.

Note that this step and the enrichment step are sometimes inverted, or an additional infra-dependent processing might take place after the enrichment. 


## Enrich entities with PIDs

We enrich the supporter and intermediary fields with ROR or Wikidata identifiers.

Usually, we have three steps to perform this enrichment:

```mermaid
flowchart LR
    A("Pre-match entities")
    B("Enrich prepared data in Google sheet")
    C("Process matched data")

    A e1@==> B
    B e2@==> C

    classDef animate stroke-dasharray: 9\,5,stroke-dashoffset: 900,animation: dash 25s linear infinite;
    class e1,e2 animate;
```

1. Run the [pid_matching.prepare_manual_matching](./data/pid_matching.py) to pre-match the entities to the ROR. This uses the [ROR affiliation API](https://ror.readme.io/docs/api-affiliation) and derives whether the given match can be automatically trusted.

    If the spreadsheet has intermediary data, it should also be pre-matched.
    I usually put the supporter matching results directly in the original dataset in a spreadsheet named `Transfers`, and the intermediary matching result in a separate sheet called `Consortiums`.


2. Export and upload the resulting results to a google sheet. We continue the enrichment there to use our custom [google_sheet_script.gs](./data/manual_review/google_sheet_script.js).

    This step consists in verifying untrusted affiliation results and adding Wikidata IDs when nor ROR record exists.


3. Download the enriched data and process it using [pid_matching.process_enriched_data](./data/pid_matching.py).

    As in step 1., the processing should also be performed on intermediaries/consortiums, if any.

Note that SciPost data enrichment process is different, cf. its dedicated [notebook](./data/preparation/scipost/run.ipynb).

## Create RawDataConfig

This is the core feature of our data preparation.

For each dataset to prepare, we define a custom configuration object, [`RawDataConfig`](./data/preparation/raw_data_config.py), that maps the input fields to our database models, along with information on how to process the fields (default value, value format, ...).
The same config can be re-used when the datasets are the same.

This also requires extra arguments:

- A valid `source` name.
- An optional year (when the data is for a given year).
- The path to the "raw" (or prepared) dataset. 


The class exposes methods to clean and import the data. 

## Generate TSOSI data file

The final step is to generate a `.json` file in a specific format that can be ingested in the next step.

This is simply done by calling the `generate_data_file` method of the `RawDataConfig` object.

It is responsible for parsing and performing various checks on the data. Errors will be raised if the provided data does not suit our standard. For example, the following cases should raise an error/warning:

* No date value (at least one date is mandatory).

* An amount is provided without a currency.

* The provided currency does not fit our sublist of supported currencies (in [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) format).

* The provided country cannot be mapped to an actual country using pycountries.

* ...

The output file of this preparation is ready to be ingested in our database.



# [Data ingestion](./data/ingestion/)

This contains the code to ingest a prepared dataset of transfers in the database.

```mermaid
flowchart LR
    A("Validate data format & source")
    B("Pre-match entities with existing ones")
    C("Create database records")
    D("Send appropriate events")

    A e1@==> B
    B e2@==> C
    C e3@==> D

    classDef animate stroke-dasharray: 9\,5,stroke-dashoffset: 900,animation: dash 25s linear infinite;
    class e1,e2,e3,e4 animate;
```

## Data format & source validation

- Parse the file to the expected data format.

- Validate that the source can be ingested. The source won't be validated when it has an associated year and there already exists another source with full data for that given year.   


## Pre-match entities with existing ones

Match the given entities with the ones in the database. The matching is made on the attached identifiers, name and country.

An entity with an identifier can only match or be matched to an entity with an identifier.
Reversely , an entity without identifier can only match or be matched  to an entity without identifier.

## Create database records

- Create Entities and related identifiers without match
- Create Transfers and matching data. 

**Note:** There's no check on the potential duplications of transfers. That's why we currently empty and refill the database when some data changes or has been corrected.

## Send "transfers created" event

Send the [transfers_created](./data/signals.py) and [identifiers_created](./data/signals.py) django signals.
Automated tasks are triggered based on that signal.


# [Data enrichment](./data/enrichment/)

This contains the code to enrich our dataset with external sources.

This is wrapped by defined [Celery tasks](./tasks.py) and scheduled using Celery Beat.
Some tasks are directly invoked when relevant signals are sent. See [signals.py](./data/signals.py) or the chart below.

The scheduled tasks are defined in the `TSOSI_CELERY_BEAT_SCHEDULE` setting.

Here is the tasks and signals workflow:

```mermaid
flowchart LR
    A("Transfers created")
    B("Identifiers created")
    C("Identifiers fetched")

    OTHER("Scheduled tasks")

    Ta("post_ingestion_pipeline")
    Tb("update_clc_fields")
    Tc("currency_rates_workflow")

    Td("fetch_empty_ror_records")
    Te("fetch_empty_wikidata_records")
    
    Tf("identifier_version_cleaning")

    Tg("process_identifier_data")
    Th("update_wiki_data")
    Ti("update_wikipedia_extract")
    Tj("update_logos")

    Tk("new_ror_identifers_from_records")
    Tl("new_wikidata_identifers_from_records")


    Tz("identifier_update")


    A a1@==> Ta
    Ta --> Tb
    Ta --> Tc

    B a2@==> Td
    B a3@==> Te

    Td -- send --> C
    Te -- send --> C

    Tg --> Tb
    Tg --> Th

    Th --> Ti
    Th --> Tj

    Tk --> Tb
    Tl --> Tb

    Tz -- send --> C
    C a4@==> Tg
    C a5@==> Tk
    C a6@==> Tl
    C a7@==> Tf


    OTHER a8@==> Tb
    OTHER a9@==> Tc
    OTHER a10@==> Th
    OTHER a11@==> Tz


    classDef signals stroke:green;
    class A,B,C signals

    classDef scheduled stroke:orange:
    class OTHER scheduled

    classDef task font\-style:italic;
    class Ta,Tb,Tc,Td,Te,Tf,Tg,Th,Ti,Tj,Tk,Tl,Tm,Tn,To,Tp,Tq,Tr,Ts,Tt,Tu,Tv,Tw,Tx,Ty,Tz task;

    classDef databaseTask color:#6d859d;
    class Ta,Tb,Tf,Tk,Tl databaseTask;


    classDef apiTask color:#954949;
    class Tc,Td,Te,Th,Ti,Tj,Tz apiTask;
    

    classDef animate stroke-dasharray: 9\,5,stroke-dashoffset: 900,animation: dash 25s linear infinite;
    class a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12 animate;
```

The enrichment consists in:

* Fetching of external PID records (ROR, Wikidata).
* Fetching of wikipedia extract and wikidata logo files.
* Processing of the above data.

The code is split in 2 files:

- [database_related.py](./data/enrichment/database_related.py) - Methods that do not request external resources.

- [api_related.py](./data/enrichment/api_related.py) - Methods relying on external data fetching.

Ideally, one should split each method/task create a template "method" class, given that everything does quite the same: select data to work with, perform method-specific stuff, log things, ...


## PID records fetching

The requests made to the registries are throttled using the token bucket algorithm implemented in [TokenBucket](./data/token_bucket.py).
The tasks are automatically re-scheduled when they're throttled, see [TsosiTask](./tasks.py).


## [Currencies](data/currencies/currency_rates.py)

This contains the code to fetch the rates of the supported currencies and to convert the transfer amounts in those currencies.

* We rely on the [BIS data portal](https://data.bis.org) to fetch the historical currency rates 

* We only fetch the rates for the timeline spanned by the transfers in the database and for the distinct currencies present in the transfer table.   