# solidfunc

An experimental functional Python API for [SolidCore](https://github.com/tangency-labs/solidcore).

This is a small academic exploration of typed, functional CAD as code, informed
by [CadQuery](https://github.com/CadQuery/cadquery),
[build123d](https://github.com/gumyr/build123d), and
[CAD as Code](https://github.com/DavidMStraub/cad-as-code-book). Its scope is a
limited set of examples for investigating API design and kernel behavior.

## Hello world

```python
import solidfunc as sf

block = sf.box(length=10, width=20, height=30)
moved = sf.translate(block, x=100)

print(sf.volume(block))  # 6000.0 mm³
print(sf.bounds(block))  # ((0.0, 0.0, 0.0), (10.0, 20.0, 30.0))
print(sf.bounds(moved))  # ((100.0, 0.0, 0.0), (110.0, 20.0, 30.0))

sf.export_step(block, "hello.step")
```

Geometry is represented by opaque `Shape` values. The current constructors
create 3D solids. Functions return new geometry and preserve their inputs.
Lengths are millimetres, volumes are cubic millimetres, and a box's `origin`
is its lower corner. Currently implemented: `box`, `cylinder`, `union`,
`intersection`, `difference`, `translate`, `volume`, `bounds`, and `export_step`.
These operations use SolidCore itself.

The example writes a STEP AP242 file that can be opened in other CAD tools.
After cloning the repository, run these commands from its root directory to
generate and display the file. Install the **OCP CAD Viewer** extension in
VS Code and start its viewer first:

```sh
uv sync --locked --inexact --config-setting build-args=--profile=dev
uv pip install --python .venv/bin/python 'cadquery>=2.8,<3' 'ocp-vscode>=4.2,<4.3'
source .venv/bin/activate
python examples/hello_world.py
python examples/view_hello.py
```

CadQuery and the viewer are installed separately into `.venv` for these examples.
They are not project dependencies. Include `--inexact` in subsequent `uv sync`
commands to keep these manually installed tools.
Use the matching 4.2.x version of the OCP CAD Viewer extension.

## Cylinders and booleans

A cylinder extends along +Z from `origin`, the centre of its base circle.
Its `radius` and `height` must be positive and finite, in millimetres.
Boolean operations take two positional operands and preserve both inputs:

```python
block = sf.box(length=10, width=10, height=10)
tool = sf.cylinder(radius=2, height=12, origin=(5, 5, -1))

drilled = block - tool  # equivalent to sf.difference(block, tool)
combined = block + tool  # equivalent to sf.union(block, tool)
shared = sf.intersection(block, tool)  # material in both

if drilled is not None:
    sf.export_step(drilled, "drilled.step")
```

An empty `intersection` or `difference` returns `None`. Results with multiple
disconnected regions stay in a single `Shape` value; STEP export preserves
all of them. `union` always returns a `Shape`.
The `+` and `-` operators have the same behavior and preserve their operands.

Kernel failures raise `sf.KernelError`, a subclass of `RuntimeError`.
Invalid dimensions raise `ValueError`; filesystem failures raise standard
`OSError` subclasses.

## Bearing pillow block

[examples/bearing_pillow_block.py](examples/bearing_pillow_block.py) reproduces
CadQuery's [parametric bearing pillow block](https://cadquery.readthedocs.io/en/latest/examples.html#a-parametric-bearing-pillow-block)
using a box, cylindrical cutters, and the `+` and `-` operators. The default
plate is 30 × 40 × 10 mm, with a 22 mm bearing hole and four counterbored
mounting holes. The modelling function takes dimensions as keyword arguments.

With the development environment activated, run:

```sh
python examples/bearing_pillow_block.py
python examples/view_pillow_block.py
```

The first script writes `pillow_block.step` in the repository root. The second
imports it with CadQuery and displays it in the running OCP CAD Viewer, using
the same optional viewing tools as the hello-world example.

## Development

### Dev container

Install Docker and VS Code's **Dev Containers** extension, open this repository,
then run **Dev Containers: Reopen in Container**. The first setup installs the
pinned Rust toolchain and Python version, builds solidfunc in editable mode,
and installs the development and viewing tools. It also generates `hello.step`
and `pillow_block.step`. The first native build takes a few minutes.

Python, Ruff, Rust Analyzer, OCP CAD Viewer, Codex, and Claude Code extensions
are configured for the container, and GitHub CLI (`gh`) is installed.
Open **OCP CAD Viewer: Open viewer**, then run:

```sh
python examples/view_pillow_block.py
pytest
```

The container's virtual environment lives at `/home/vscode/.venvs/solidfunc`;
`python` and the development tools are already on `PATH`. uv downloads and Rust
build outputs are cached in a Docker volume. To rebuild after Rust changes
while retaining the separately installed viewing tools, use:

```sh
uv sync --locked --inexact --config-setting build-args=--profile=dev
```

Maturin writes the native extension into the source tree. When switching
between host and container development, rebuild it for that environment with
`uv sync --locked --inexact --reinstall-package solidfunc --config-setting build-args=--profile=dev`.

#### Coding assistants and persistent state

Open the Codex and Claude Code panels in the container window and sign in on
first use. For GitHub CLI, run `gh auth login` in the container terminal.
Saved assistant memory, conversations, and settings are kept in Docker volumes
scoped to this checkout, along with GitHub CLI configuration and VS Code's
remote data:

| Directory | Persistent state |
| --- | --- |
| `/home/vscode/.codex` | Codex configuration, saved sessions, and memory |
| `/home/vscode/.claude` | Claude Code configuration, saved sessions, and auto memory |
| `/home/vscode/.config/gh` | GitHub CLI configuration and file-based authentication |
| `/home/vscode/.vscode-server/data` | VS Code remote settings and extension UI state |

`CLAUDE_CONFIG_DIR` points to the mounted Claude directory so its global
`.claude.json` file is also retained. See the official
[Codex state locations](https://learn.chatgpt.com/docs/config-file/config-advanced#config-and-state-locations)
and [Claude Code dev container guidance](https://code.claude.com/docs/en/devcontainer#persist-authentication-and-settings-across-rebuilds).
The fixed workspace path keeps project-specific memory associated with the
same project after a rebuild. Rebuilds retain these volumes; deleting the
volumes removes their state. Project instruction files such as `AGENTS.md`
and `CLAUDE.md` remain in the mounted repository.

### Local setup

Install [uv](https://docs.astral.sh/uv/) and [Rust](https://rustup.rs/), then:

```sh
git clone https://github.com/DavidMStraub/solidfunc.git
cd solidfunc
uv sync --locked --config-setting build-args=--profile=dev
uv run --no-sync python examples/hello_world.py
uv run --no-sync pytest
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
cargo fmt --all --check
cargo clippy --locked --all-targets -- -D warnings
```

The project uses a mixed Python/Rust layout: the public typed API lives in
`python/solidfunc`, and the private PyO3 extension in `src/lib.rs` calls
`solidcore-ops` and `solidcore-step`. Maturin builds and installs the extension
during `uv sync`; the development command above uses the faster debug profile
and installs the package in editable mode in `.venv`. Python changes take effect
immediately; after changing Rust code, rerun that `uv sync` command to rebuild
the extension. Python 3.11+ is supported using the CPython stable ABI (`abi3`).

SolidCore is pinned to commit `cb9bee4bb9f56880c9973a9f8e99c83fdec24ad3`
in `Cargo.toml`; `Cargo.lock` and `uv.lock` pin the resolved dependencies.
Updating the kernel is an explicit change to that revision followed by a
lockfile update and the geometry checks.

To check STEP exchange against CadQuery's independent kernel:

```sh
uv run --no-sync --with 'cadquery>=2.8,<3' pytest tests/test_step_export.py
```

The CadQuery round-trip tests are skipped when that optional dependency is absent.

## Builds and publishing

```sh
uv build
uv run --no-sync twine check dist/*
```

On pushes to `main` and pull requests, CI checks Python formatting, lint,
typing, geometry behavior, and CadQuery STEP exchange, plus Rust formatting
and clippy. It tests Python 3.11 and 3.14 on Linux.

The full distribution builds run for releases or when **Build distributions**
is triggered manually. They build and test native wheels for Linux, Windows,
and macOS, and verify a wheel rebuilt from the source distribution.

Publishing is a separate **Publish to PyPI** workflow triggered by a published
GitHub release. It checks that the tag matches the package version, builds and
tests the distributions, and publishes with OIDC trusted publishing.

Before the first release, log in to PyPI with two-factor authentication enabled
and register a pending GitHub publisher in your
[publishing settings](https://pypi.org/manage/account/publishing/):

| Setting | Value |
| --- | --- |
| PyPI project | `solidfunc` |
| GitHub owner | `DavidMStraub` |
| Repository | `solidfunc` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

The initial Cargo version `0.1.0-alpha.1` maps to Python version `0.1.0a1`.
Publish a GitHub release tagged `v0.1.0a1` and mark it as a pre-release to
release it. No PyPI API token is needed. A pending publisher does not reserve
the project name: the first successful upload creates the project and claims
the name, as described in the
[PyPI documentation](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
Creating the repository or pushing a commit does not publish a package.

## License

solidfunc is MIT licensed. SolidCore and its SMLib-derived code are Apache-2.0
licensed; the distribution includes the corresponding upstream notices.
