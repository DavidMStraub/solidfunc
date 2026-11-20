# solidfunc

[![PyPI](https://img.shields.io/pypi/v/solidfunc)](https://pypi.org/project/solidfunc/)
[![Python](https://img.shields.io/pypi/pyversions/solidfunc)](https://pypi.org/project/solidfunc/)
[![CI](https://github.com/DavidMStraub/solidfunc/actions/workflows/ci.yml/badge.svg)](https://github.com/DavidMStraub/solidfunc/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/DavidMStraub/solidfunc/blob/main/LICENSE)

solidfunc is a typed, functional Python library for code-based CAD, built on
[SolidCore](https://github.com/tangency-labs/solidcore), a B-rep geometry
kernel written in Rust. You build solids from primitives and planar profiles,
place and combine them, select faces and edges, round and chamfer edges, and
export STEP files that open in any CAD tool.

## Install

```sh
pip install solidfunc
```

Wheels are available for Linux, macOS, and Windows on Python 3.11 and later.

## A first part

A plate with a hole whose rim is rounded, exported as STEP:

```python
import solidfunc as sf

plate = sf.box(size_x=80, size_y=50, size_z=10)
hole = sf.cylinder(diameter=20, height=10)
part = plate - hole

top = max(sf.faces(part), key=lambda face: face.centroid[2])
hole_edge = [edge for edge in sf.edges(top) if edge.kind == "circle"]
part = sf.fillet(part, hole_edge, radius=2.0)

print(f"{sf.volume(part):.3f} mm³")
sf.export_step(part, "plate.step")
```

Every operation returns a new value and leaves its inputs unchanged. Lengths
are in millimetres and angles in degrees. Selection is plain Python over
typed face and edge data. See the
[API reference](https://github.com/DavidMStraub/solidfunc/blob/main/API.md)
for signatures and conventions.

## Gallery

Parts from the chapters of
[CAD as Code](https://github.com/DavidMStraub/cad-as-code-book), rebuilt in
solidfunc.

| | |
|---|---|
| ![Clutch brick](https://raw.githubusercontent.com/DavidMStraub/solidfunc/main/docs/gallery/clutch-brick.png) | ![Battery tray](https://raw.githubusercontent.com/DavidMStraub/solidfunc/main/docs/gallery/battery-tray.png) |
| [**Clutch brick**](https://github.com/DavidMStraub/solidfunc/blob/main/examples/clutch_brick.py): studs placed on the top face with `place()` | [**Battery tray**](https://github.com/DavidMStraub/solidfunc/blob/main/examples/battery_tray.py): cell pockets, mirrored holes, and a lead-in round selected by radius |
| ![Swept elbow](https://raw.githubusercontent.com/DavidMStraub/solidfunc/main/docs/gallery/swept-elbow.png) | ![Round-to-rectangle duct](https://raw.githubusercontent.com/DavidMStraub/solidfunc/main/docs/gallery/duct.png) |
| [**Swept elbow**](https://github.com/DavidMStraub/solidfunc/blob/main/examples/swept_elbow.py): a hollow section swept along a cornered path | [**Duct**](https://github.com/DavidMStraub/solidfunc/blob/main/examples/duct.py): a loft from a circle to a rectangle |

## Viewing parts

Install PyVista with `pip install pyvista`, then call `show()`:

```python
from solidfunc.view import show

show(part)
```

Pass `screenshot="part.png"` to save a PNG. In Jupyter, `show()` displays a
static preview by default. For an interactive view, install `pyvista[jupyter]`
and pass `jupyter_backend="client"`.

## About this project

### Motivation

The best-known open-source code-CAD libraries for Python,
[CadQuery](https://github.com/CadQuery/cadquery) and
[build123d](https://github.com/gumyr/build123d), are built on the
[OpenCascade Technology (OCCT)](https://github.com/Open-Cascade-SAS/OCCT)
kernel. solidfunc asks how much of a parametric code-CAD API depends on its
kernel: which ideas carry over to a different kernel unchanged, and which
are really properties of OCCT.

### Scope

solidfunc is a small academic experiment, not a replacement for anything. For
real work, use CadQuery or build123d. My book
[CAD as Code](https://github.com/DavidMStraub/cad-as-code-book) uses
CadQuery's functional API throughout, and solidfunc borrows many ideas from
both projects.

The first part above is chapter 2 of the book. In CadQuery's functional API
it reads like this, and both versions give the same volume, 36802.063 mm³:

```python
from cadquery import func as cf

plate = cf.box(80, 50, 10)
hole = cf.cylinder(d=20, h=10)
part = plate - hole
hole_edge = part.faces(">Z").edges("%CIRCLE")
result = part.fillet(2.0, [hole_edge])
```

The structure is the same. The differences are in the details: solidfunc
names every dimension, and it selects with Python over typed data where
CadQuery uses selector strings.

### Findings

- **The kernel's data model shapes the API.** SolidCore builds solids from
  geometric sketch records (segments, loops, regions), not from OCCT's
  topological edges and wires. solidfunc's `Curve2D`, `Path2D`, and `Profile`
  mirror those records, and topology (`Face`, `Edge`, `Vertex`) only exists
  inside a solid.
- **How a kernel stores surfaces shows up in selection.** SolidCore stores a
  round on a straight edge as a cone with a zero half-angle, and `revolve`
  produces B-spline surfaces even for a cone or a sphere. solidfunc reports
  the first as a cylinder and documents the second, but "select the
  cylindrical faces" means something different on each kernel.
- **Immutability has a price.** SolidCore's booleans consume their operands,
  so solidfunc copies its inputs to keep every value unchanged.
- **Kernel features become API.** SolidCore unites many bodies in one call,
  which became `union(*shapes)`.

### Coverage

solidfunc covers what the experiment needs: single solids from primitives,
extrusions, revolutions, lofts, and sweeps; booleans; placement; fillets and
chamfers; face and edge queries; and STEP import and export. Assemblies,
colours, open sheets and shells, and 2D operations on profiles are outside
its scope. Releases are alphas, and the API can change between them.

## Development

To build from source, install [uv](https://docs.astral.sh/uv/) and
[Rust](https://rustup.rs/), then run from the cloned repository:

```sh
uv sync --locked --config-setting build-args=--profile=dev
uv run --no-sync pytest
uv run --no-sync python examples/hello_world.py
```

`examples/render_gallery.py` regenerates the gallery images.

## Citing

If you use solidfunc in your work, please cite it; GitHub's "Cite this
repository" button gives the reference from
[CITATION.cff](https://github.com/DavidMStraub/solidfunc/blob/main/CITATION.cff).

## License

solidfunc is MIT licensed. SolidCore and its SMLib-derived code are Apache-2.0
licensed. The distribution includes the corresponding upstream notices.
