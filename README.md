# solidfunc

An experimental functional Python API for [SolidCore](https://github.com/tangency-labs/solidcore).

This is a small academic exploration of typed, functional CAD as code, informed
by [CadQuery](https://github.com/CadQuery/cadquery),
[build123d](https://github.com/gumyr/build123d), and
[CAD as Code](https://github.com/DavidMStraub/cad-as-code-book). Its scope is a
limited set of examples for investigating API design and kernel behavior.

## Installation

To install from source, clone this repository. From its root, with [uv](https://docs.astral.sh/uv/)
and [Rust](https://rustup.rs/) installed, run these commands to build the package
and generate `hello.step`:

```sh
uv sync --locked --config-setting build-args=--profile=dev
uv run --no-sync python examples/hello_world.py
```

solidfunc supports Python 3.11 and later. In VS Code, you can also open the
repository with **Dev Containers: Reopen in Container** to use the preconfigured
environment.

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

From the repository root, run:

```sh
uv run --no-sync python examples/bearing_pillow_block.py
```

Open `pillow_block.step` in a CAD tool that supports STEP. The repository also
includes [viewer scripts](examples/) for CadQuery and OCP CAD Viewer, both
preinstalled in the dev container. In the container, open **OCP CAD Viewer: Open
viewer** in VS Code and run `python examples/view_pillow_block.py`.

## License

solidfunc is MIT licensed. SolidCore and its SMLib-derived code are Apache-2.0
licensed; the distribution includes the corresponding upstream notices.
