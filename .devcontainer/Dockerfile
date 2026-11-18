FROM mcr.microsoft.com/devcontainers/base:bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libegl1 \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PROJECT_ENVIRONMENT=/home/vscode/.venvs/solidfunc \
    CARGO_TARGET_DIR=/home/vscode/.cache/solidfunc-target \
    UV_LINK_MODE=copy \
    PATH=/home/vscode/.venvs/solidfunc/bin:/home/vscode/.cargo/bin:/home/vscode/.local/bin:${PATH}

COPY --chown=vscode:vscode .python-version rust-toolchain.toml /tmp/solidfunc-toolchain/

USER vscode

# Give new state volumes the development user's ownership before VS Code starts.
RUN mkdir -p /home/vscode/.codex /home/vscode/.claude \
    /home/vscode/.config/gh /home/vscode/.vscode-server/data

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain none --profile minimal

# Read the same toolchain pins as local development and CI.
RUN cd /tmp/solidfunc-toolchain \
    && rustup toolchain install --no-self-update \
    && rustup component add rust-src \
    && uv python install

WORKDIR /workspaces/solidfunc
