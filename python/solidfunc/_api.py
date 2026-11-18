"""The public functional interface, independent of binding details."""

from math import isfinite
from os import PathLike
from pathlib import Path
from typing import TypeAlias

from . import _core
from ._core import Shape

Point3D: TypeAlias = tuple[float, float, float]
Bounds: TypeAlias = tuple[Point3D, Point3D]


def _positive(name: str, value: float) -> None:
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")


def box(
    *,
    length: float,
    width: float,
    height: float,
    origin: Point3D = (0.0, 0.0, 0.0),
) -> Shape:
    """Construct a box extending along +X, +Y and +Z from its lower corner.

    Dimensions must be positive and finite. ``origin`` is the lower corner,
    not the centre. All coordinates and dimensions are in millimetres.
    """
    for name, value in (("length", length), ("width", width), ("height", height)):
        _positive(name, value)
    return _core._box(origin, (length, width, height))


def cylinder(
    *, radius: float, height: float, origin: Point3D = (0.0, 0.0, 0.0)
) -> Shape:
    """Construct a cylinder along +Z from its base centre, in millimetres.

    ``radius`` and ``height`` must be positive and finite. ``origin`` is the
    centre of the lower circular face.
    """
    _positive("radius", radius)
    _positive("height", height)
    return _core._cylinder(origin, radius, height)


def union(left: Shape, right: Shape, /) -> Shape:
    """Return the material in either operand, preserving both inputs.

    Disconnected regions are kept together in one opaque geometry value.
    """
    return _core._union(left, right)


def intersection(left: Shape, right: Shape, /) -> Shape | None:
    """Return the shared volume, or ``None`` if empty, preserving both inputs."""
    return _core._intersection(left, right)


def difference(left: Shape, right: Shape, /) -> Shape | None:
    """Subtract ``right`` from ``left``, preserving both inputs.

    Return ``None`` when no material remains. Disconnected remaining regions
    are kept together in one opaque geometry value.
    """
    return _core._difference(left, right)


def volume(shape: Shape, *, relative_accuracy: float = 1e-9) -> float:
    """Measure enclosed volume in mm³ at the requested relative accuracy."""
    _positive("relative_accuracy", relative_accuracy)
    return _core._volume(shape, relative_accuracy)


def translate(shape: Shape, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Shape:
    """Return an independent translated shape, leaving ``shape`` unchanged."""
    return _core._translate(shape, (x, y, z))


def bounds(shape: Shape) -> Bounds:
    """Return axis-aligned minimum and maximum corners in millimetres."""
    # PyO3 converts Rust arrays to lists; expose tuples consistently in Python.
    lower, upper = _core._bounds(shape)
    return (lower[0], lower[1], lower[2]), (upper[0], upper[1], upper[2])


def export_step(shape: Shape, path: str | PathLike[str], *, name: str = "Part") -> None:
    """Write a shape as STEP AP242, preserving its geometry and placement.

    ``path`` may be a string or a path object. An existing file is overwritten.
    ``name`` labels the shape in the exported file. Length units are millimetres.
    Geometry conversion completes before the output file is opened.
    """
    destination = Path(path)
    text = _core._step_text(shape, destination.name, name)
    destination.write_text(text, encoding="utf-8", newline="\n")
