#!/usr/bin/env bash
set -euo pipefail

# Docker cache and state volumes need to be writable by the development user.
sudo chown "$(id -u):$(id -g)" \
    /home/vscode/.cache \
    /home/vscode/.codex \
    /home/vscode/.claude \
    /home/vscode/.config/gh \
    /home/vscode/.vscode-server/data

uv sync --locked --inexact --config-setting build-args=--profile=dev
uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" \
    'cadquery>=2.8,<3' 'ocp-vscode>=4.2,<4.3'

python examples/hello_world.py
python examples/bearing_pillow_block.py
