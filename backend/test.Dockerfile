FROM python:3.12-slim

# Real time output from python (stdout and stderr) without buffer
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# UNIX packages
RUN apt-get update && apt-get install -y curl \
    git

# Python deps (managed via Poetry)
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV CONTAINER_HOME="/root"

ENV PATH="$CONTAINER_HOME/.local/bin:$PATH"

# Install directly in the global container's Python.
# This must be done differently if other stuff requires Python too.
RUN poetry config virtualenvs.create false

COPY backend/pyproject.toml backend/poetry.lock /app/
RUN poetry install --no-root

CMD ["sleep", "infinity"]

