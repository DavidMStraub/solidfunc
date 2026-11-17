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

Geometry is opaque. Functions return new geometry and preserve their inputs.
Lengths are millimetres, volumes are cubic millimetres, and a box's `origin`
is its lower corner. Currently implemented: `box`, `translate`, `volume`,
`bounds`, and `export_step`. This initial example exercises SolidCore itself.

The example writes a STEP AP242 file that can be opened in other CAD tools.
After cloning the repository, run these commands from its root directory to
generate and display the file. Install the **OCP CAD Viewer** extension in
VS Code and start its viewer first:

```sh
uv sync --locked --inexact --config-setting build-args=--profile=dev
uv pip install --python .venv/bin/python 'cadquery>=2.8,<3' 'ocp-vscode>=3,<4'
source .venv/bin/activate
python examples/hello_world.py
python examples/view_hello.py
```

CadQuery and the viewer are installed separately into `.venv` for these examples.
They are not project dependencies. Include `--inexact` in subsequent `uv sync`
commands to keep these manually installed tools.

## Development

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

CI checks Python formatting, lint, typing, and geometry behavior, plus Rust
formatting and clippy. The reusable wheel workflow builds and tests native
wheels for Linux, Windows, and macOS, and builds a source distribution.
The **Build distributions** workflow can also be run manually.

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
