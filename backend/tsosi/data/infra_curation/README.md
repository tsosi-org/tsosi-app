# Infrastructure curation bot

Comments the `[Infra curation]` issues with the metadata found about the
requested infrastructure, as a table to review before adding it to TSOSI.

## How it works

The issues are created with the
[Infrastructure curation](../../../../.github/ISSUE_TEMPLATE/infra-curation.yml)
issue form: the title holds the infrastructure name, the body the asking
institution and the ROR, Wikidata or TSOSI ID (or URL) of the infrastructure.
Issues created with the form are added to the
[curation project](https://github.com/orgs/tsosi-org/projects/7).

The bot (`curation.py`):

1. Fetches the record of the given ID. Issues without an ID only get a
   warning: the bot doesn't search the infrastructure by name.
2. Completes the ROR, Wikidata and TSOSI records from each other's links.
3. Looks the infrastructure up in the SCOSS Family, the POSI adopters, the
   Barcelona Declaration signatories and Infra Finder (see
   `tsosi/data/infra_lists.py`), by ROR ID, website domain or name.
4. Posts the metadata table as a comment, and updates that comment on the
   next runs (it is identified by a hidden marker).

Description and how-to-support are only filled from an existing TSOSI entity.

## GitHub workflow

`.github/workflows/infra-curation-bot.yaml` runs the bot:

- when an `[Infra curation]` issue is opened, edited or reopened;
- manually (_Actions > Infrastructure curation bot > Run workflow_), for one
  issue or for all the open issues whose title starts with `[Infra curation]`
  and that are not yet commented (or all of them with `force`).

It only needs the default workflow token.

Issue events run the workflow file of the default branch only.

## Run locally

```bash
# Print the comment of an issue without posting it
poetry run python -m tsosi.data.infra_curation 304 --dry-run
# Post/update the comments of all the open [Infra curation] issues
GITHUB_TOKEN=... poetry run python -m tsosi.data.infra_curation
```

The repository defaults to `tsosi-org/tsosi-app`, set `GITHUB_REPOSITORY` to
use another one. Without `GITHUB_TOKEN`, GitHub allows only 60 requests per
hour: enough for a few dry runs.

The package doesn't use Django or the database.
