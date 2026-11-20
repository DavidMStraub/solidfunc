"""Solid construction, transformations, measurements, and STEP export."""

from math import isfinite, radians
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


def box(*, size_x: float, size_y: float, size_z: float) -> Shape:
    """Construct a box centred on the Z axis with its base at z = 0.

    ``size_x``, ``size_y``, and ``size_z`` are the positive, finite dimensions
    along X, Y, and Z in millimetres. The box spans ``±size_x / 2`` and
    ``±size_y / 2`` and rises from z = 0 to ``size_z``, matching ``cylinder``.
    Place it with ``translate`` or ``place``.
    """
    for name, value in (("size_x", size_x), ("size_y", size_y), ("size_z", size_z)):
        _positive(name, value)
    return _core._box((-size_x / 2, -size_y / 2, 0.0), (size_x, size_y, size_z))


def cylinder(*, radius: float, height: float) -> Shape:
    """Construct a cylinder on the Z axis with its base centre at the origin.

    ``radius`` is the radius of each circular face and ``height`` is the
    distance between them, both positive and finite, in millimetres. The
    cylinder rises from z = 0 to ``height``. Place it with ``translate`` or
    ``place``.
    """
    _positive("radius", radius)
    _positive("height", height)
    return _core._cylinder((0.0, 0.0, 0.0), radius, height)


def union(left: Shape, right: Shape, /) -> Shape:
    """Return the material in either operand, preserving both inputs.

    Disconnected regions are kept together in one opaque geometry value.
    """
    return _core._union(left, right)


def intersection(left: Shape, right: Shape, /) -> Shape | None:
    """Return the solid material shared by ``left`` and ``right``.

    Return ``None`` when there is no shared solid material. Both inputs are
    preserved.
    """
    return _core._intersection(left, right)


def difference(left: Shape, right: Shape, /) -> Shape | None:
    """Subtract ``right`` from ``left``, preserving both inputs.

    Return ``None`` when no material remains. Disconnected remaining regions
    are kept together in one opaque geometry value. The ``-`` operator does
    the same but raises ``EmptyResultError`` instead of returning ``None``.
    """
    return _core._difference(left, right)


def volume(shape: Shape, *, relative_tolerance: float = 1e-9) -> float:
    """Return the volume of ``shape`` in cubic millimetres.

    ``relative_tolerance`` is a positive, finite, dimensionless tolerance
    requested for the kernel's volume integration.
    """
    _positive("relative_tolerance", relative_tolerance)
    return _core._volume(shape, relative_tolerance)


def translate(shape: Shape, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Shape:
    """Return a translated copy of ``shape``.

    ``x``, ``y``, and ``z`` are signed offsets in millimetres along the
    world axes. Each defaults to zero and must be finite.
    """
    return _core._translate(shape, (x, y, z))


def rotate(
    shape: Shape,
    *,
    axis_direction: Point3D,
    angle_deg: float,
    axis_origin: Point3D = (0.0, 0.0, 0.0),
) -> Shape:
    """Return a rotated copy of ``shape``.

    ``axis_direction`` is a finite, nonzero (x, y, z) direction vector. It need not
    have unit length. ``axis_origin`` is a point on the rotation axis, in
    millimetres, and defaults to the world origin. ``angle_deg`` is a finite
    angle in degrees. Positive angles follow the right-hand rule.
    """
    return _core._rotate(shape, axis_origin, axis_direction, radians(angle_deg))


def mirror(
    shape: Shape,
    *,
    normal: Point3D,
    origin: Point3D = (0.0, 0.0, 0.0),
) -> Shape:
    """Reflect a shape across the plane through ``origin`` normal to ``normal``.

    ``origin`` is a point in world millimetres. ``normal`` is a finite,
    nonzero direction vector and need not have unit length.
    """
    return _core._mirror(shape, origin, normal)


def bounds(shape: Shape) -> Bounds:
    """Return the world-axis-aligned bounds of ``shape`` in millimetres.

    The result is ``(minimum, maximum)``, with each corner an (x, y, z) tuple.
    """
    # PyO3 converts Rust arrays to lists; expose tuples consistently in Python.
    lower, upper = _core._bounds(shape)
    return (lower[0], lower[1], lower[2]), (upper[0], upper[1], upper[2])


def export_step(shape: Shape, path: str | PathLike[str], *, name: str = "Part") -> None:
    """Write a shape as STEP AP242, preserving its geometry and placement.

    ``shape`` is the solid to export. ``path`` is a string or path object.
    An existing file is overwritten. ``name`` labels the solid in the file.
    Length units are millimetres.
    Geometry conversion completes before the output file is opened.
    """
    destination = Path(path)
    text = _core._step_text(shape, destination.name, name)
    destination.write_text(text, encoding="utf-8", newline="\n")


def import_step(path: str | PathLike[str], /) -> Shape:
    """Read STEP solids as a single shape in world millimetres.

    ``path`` is a string or path object. Multiple solid occurrences are
    placed and united. Reader or conversion failures raise ``KernelError``.
    Filesystem errors propagate as ``OSError`` subclasses.
    """
    return _core._import_step(Path(path).read_bytes().decode("latin-1"))
