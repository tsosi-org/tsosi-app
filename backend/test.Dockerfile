FROM python:3.12-slim

# ENV TODAY="$(date +'%Y-%m-%d')"
LABEL org.opencontainers.image.created="$(date +'%Y-%m-%d')"
LABEL org.opencontainers.image.source="https://github.com/tsosi-org/tsosi-app" 
LABEL org.opencontainers.image.authors="guillaume.alzieu@univ-grenoble-alpes.fr"
LABEL org.opencontainers.image.title="TSOSI Backend test env"
LABEL org.opencontainers.image.description="Environnement used to test tsosi-app backend Django application"
# Real time output from python (stdout and stderr) without buffer
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# UNIX packages
RUN apt-get update && apt-get install -y curl \
    git

# Python deps (managed via Poetry)
ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV CONTAINER_HOME="/root"

ENV PATH="$CONTAINER_HOME/.local/bin:$PATH"

# Install directly in the global container's Python.
# This must be done differently if other stuff requires Python too.
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root

CMD ["sleep", "infinity"]

