apt-get update && apt-get install -y openssh-client \
    curl \
    git \
    libpq5 # For postgresql

# Install poetry for Python deps
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.in-project true

# Web server used in prod ? Nginx + GUnicorn to serve the python wgsi app.
