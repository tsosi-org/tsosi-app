FROM mcr.microsoft.com/devcontainers/python:3.12

# Real time output from python (stdout and stderr) without buffer
ENV PYTHONUNBUFFERED=1

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl \
    git

# Python deps (managed via Poetry)
# Install poetry container-wide
ENV POETRY_HOME=/etc/poetry
ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN ln -sf "$POETRY_HOME/venv/bin/poetry" /usr/bin/poetry

# We use a .venv folder directly in the repo to install python deps.
# Packages are installed via a postCreateCommand in devcontainer.json
RUN poetry config virtualenvs.in-project true

# FRONT-END deps - Install node & npm using nvm
RUN mkdir /usr/local/nvm
ENV NVM_DIR=/usr/local/nvm
ENV NODE_VERSION=24.2.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
RUN \. "$NVM_DIR/nvm.sh" \
    && nvm install $NODE_VERSION
# Create symlinks for easy use of node & npm
RUN ln -sf "$NVM_DIR/versions/node/v$NODE_VERSION/bin/node" /usr/bin/node
RUN ln -sf "$NVM_DIR/versions/node/v$NODE_VERSION/bin/npm" /usr/bin/npm
RUN node -v
RUN npm -v

# JS Packages are installed via a postCreateCommand in devcontainer.json

CMD ["sleep", "infinity"]
