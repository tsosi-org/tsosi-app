FROM mcr.microsoft.com/devcontainers/python:3.12

# Real time output from python (stdout and stderr) without buffer
ENV PYTHONUNBUFFERED=1


# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl \
    git

# Python deps (managed via Poetry)
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV CONTAINER_HOME="/root"
ENV PATH="$CONTAINER_HOME/.local/bin:$PATH"
# We use a .venv folder directly in the repo to install python deps.
# Packages are installed via a postCreateCommand in devcontainer.json
RUN poetry config virtualenvs.in-project true
# Log folder used by default by the app
RUN mkdir /var/log/tsosi/

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
