poetry run python manage.py generate_data_file /workspaces/tsosi-app/data/raw/2025-12-15_uga_full.xlsx
mv /workspaces/tsosi-app/backend/_no_git/fixtures/_exports/2025-12-18_default_full.json ../data/prepared/
poetry run python manage.py ingest_file /workspaces/tsosi-app/data/prepared/2025-12-18_default_full.json