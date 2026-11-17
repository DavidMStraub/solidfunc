"""The public functional interface, independent of binding details."""

from math import isfinite
from os import PathLike
from pathlib import Path
from typing import TypeAlias

from . import _core
from ._core import Solid

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
) -> Solid:
    """Construct a box extending along +X, +Y and +Z from its lower corner.

    Dimensions must be positive and finite. ``origin`` is the lower corner,
    not the centre. All coordinates and dimensions are in millimetres.
    """
    for name, value in (("length", length), ("width", width), ("height", height)):
        _positive(name, value)
    return _core._box(origin, (length, width, height))


def volume(solid: Solid, *, relative_accuracy: float = 1e-9) -> float:
    """Measure enclosed volume in mm³ at the requested relative accuracy."""
    _positive("relative_accuracy", relative_accuracy)
    return _core._volume(solid, relative_accuracy)


def translate(solid: Solid, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Solid:
    """Return an independent translated solid, leaving ``solid`` unchanged."""
    return _core._translate(solid, (x, y, z))


def bounds(solid: Solid) -> Bounds:
    """Return axis-aligned minimum and maximum corners in millimetres."""
    # PyO3 converts Rust arrays to lists; expose tuples consistently in Python.
    lower, upper = _core._bounds(solid)
    return (lower[0], lower[1], lower[2]), (upper[0], upper[1], upper[2])


def export_step(solid: Solid, path: str | PathLike[str], *, name: str = "Part") -> None:
    """Write a solid as STEP AP242, preserving its geometry and placement.

    ``path`` may be a string or a path object. An existing file is overwritten.
    ``name`` labels the solid in the exported file. Length units are millimetres.
    Geometry conversion completes before the output file is opened.
    """
    destination = Path(path)
    text = _core._step_text(solid, destination.name, name)
    destination.write_text(text, encoding="utf-8", newline="\n")
