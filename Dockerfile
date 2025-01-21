FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y openssh-client \
    curl \
    git \
    bash-completion \
    libpq5

WORKDIR /app

# Install poetry & Python dependencies
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV CONTAINER_HOME="/root"
ENV PATH="$CONTAINER_HOME/.local/bin:$PATH"

RUN poetry config virtualenvs.create false

COPY backend/pyproject.toml backend/poetry.lock /app/
RUN poetry install --no-root

EXPOSE 8000

# Install front dev dependencies.
RUN curl -fsSL https://deb.nodesource.com/setup_23.x | bash - \
    && apt-get install -y nodejs

RUN node --version
RUN npm --version

EXPOSE 5173

CMD ["sleep", "infinity"]
