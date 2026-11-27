"""Solid construction, transformations, measurements, and STEP export."""

from math import isfinite, radians
from os import PathLike
from pathlib import Path
from typing import NamedTuple, TypeAlias, overload

from . import _core
from ._core import Shape

Point3D: TypeAlias = tuple[float, float, float]


class Bounds(NamedTuple):
    """World-axis-aligned bounds in millimetres; unpacks as ``(min, max)``."""

    min: Point3D
    max: Point3D

    @property
    def size(self) -> Point3D:
        """Return the extent along X, Y, and Z."""
        (x0, y0, z0), (x1, y1, z1) = self
        return x1 - x0, y1 - y0, z1 - z0

    @property
    def center(self) -> Point3D:
        """Return the midpoint of the box."""
        (x0, y0, z0), (x1, y1, z1) = self
        return (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2


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


def _radius(
    radius: float | None,
    diameter: float | None,
    *,
    prefix: str = "",
    allow_zero: bool = False,
) -> float:
    radius_name, diameter_name = f"{prefix}radius", f"{prefix}diameter"
    if (radius is None) == (diameter is None):
        raise ValueError(f"supply exactly one of {radius_name} and {diameter_name}")
    name, value = (
        (radius_name, radius) if radius is not None else (diameter_name, diameter)
    )
    assert value is not None
    if allow_zero:
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and at least zero")
    else:
        _positive(name, value)
    return value if radius is not None else value / 2


@overload
def cylinder(*, radius: float, height: float) -> Shape: ...
@overload
def cylinder(*, diameter: float, height: float) -> Shape: ...
def cylinder(
    *, radius: float | None = None, diameter: float | None = None, height: float
) -> Shape:
    """Construct a cylinder on the Z axis with its base centre at the origin.

    Give exactly one of ``radius`` or ``diameter`` for the circular faces.
    ``height`` is the distance between them. All are positive and finite,
    in millimetres. The cylinder rises from z = 0 to ``height``. Place it
    with ``translate`` or ``place``.
    """
    size = _radius(radius, diameter)
    _positive("height", height)
    return _core._cylinder((0.0, 0.0, 0.0), size, height)


@overload
def sphere(*, radius: float) -> Shape: ...
@overload
def sphere(*, diameter: float) -> Shape: ...
def sphere(*, radius: float | None = None, diameter: float | None = None) -> Shape:
    """Construct a sphere on the Z axis resting on z = 0.

    Give exactly one of ``radius`` or ``diameter``, positive and finite, in
    millimetres. Like the other primitives, the sphere is centred in X and Y
    with its base at z = 0, so its centre is at z = ``radius``. Place it with
    ``translate`` or ``place``.
    """
    size = _radius(radius, diameter)
    return _core._sphere((0.0, 0.0, size), size)


@overload
def cone(*, base_radius: float, top_radius: float, height: float) -> Shape: ...
@overload
def cone(*, base_diameter: float, top_diameter: float, height: float) -> Shape: ...
def cone(
    *,
    base_radius: float | None = None,
    base_diameter: float | None = None,
    top_radius: float | None = None,
    top_diameter: float | None = None,
    height: float,
) -> Shape:
    """Construct a cone or frustum on the Z axis with its base centre at the origin.

    Give the base as exactly one of ``base_radius`` or ``base_diameter``, and
    the top as exactly one of ``top_radius`` or ``top_diameter``, in
    millimetres. The base is positive. The top is zero for a pointed cone and
    may be larger than the base, but not equal to it; use ``cylinder`` for
    that. The cone rises from z = 0 to ``height``.
    """
    base = _radius(base_radius, base_diameter, prefix="base_")
    top = _radius(top_radius, top_diameter, prefix="top_", allow_zero=True)
    _positive("height", height)
    if top == base:
        raise ValueError("top and base are equal; use cylinder() instead")
    return _core._cone((0.0, 0.0, 0.0), base, top, height)


def torus(*, major_radius: float, minor_radius: float) -> Shape:
    """Construct a ring torus around the Z axis resting on z = 0.

    ``major_radius`` is the distance from the Z axis to the centre of the
    tube, and ``minor_radius`` the tube's radius, in millimetres. Both are
    positive and finite, and the minor radius is smaller than the major one.
    The torus is centred in X and Y and rises from z = 0 to
    ``2 * minor_radius``.
    """
    _positive("major_radius", major_radius)
    _positive("minor_radius", minor_radius)
    if minor_radius >= major_radius:
        raise ValueError("minor_radius must be smaller than major_radius")
    return _core._torus((0.0, 0.0, minor_radius), major_radius, minor_radius)


def union(shape: Shape, /, *shapes: Shape) -> Shape:
    """Return the material in any operand, preserving all inputs.

    Accepts one or more shapes, so ``union(*parts)`` combines a whole list
    in one kernel operation. Disconnected regions are kept together in one
    opaque geometry value. ``left + right`` unites two shapes.
    """
    if len(shapes) == 1:
        return _core._union(shape, shapes[0])
    return _core._union_all([shape, *shapes])


def intersection(left: Shape, right: Shape, /) -> Shape | None:
    """Return the solid material shared by ``left`` and ``right``.

    Return ``None`` when there is no shared solid material. Both inputs are
    preserved. The ``&`` operator does the same but raises
    ``EmptyResultError`` instead of returning ``None``.
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


def area(shape: Shape, *, relative_tolerance: float = 1e-9) -> float:
    """Return the surface area of ``shape`` in square millimetres.

    The area of every face is counted once. ``relative_tolerance`` is a
    positive, finite, dimensionless tolerance requested for the kernel's
    integration.
    """
    _positive("relative_tolerance", relative_tolerance)
    return _core._area(shape, relative_tolerance)


def centroid(shape: Shape, *, relative_tolerance: float = 1e-9) -> Point3D:
    """Return the centroid of the volume of ``shape`` in world millimetres.

    This is the centre of mass at uniform density. ``relative_tolerance``
    is a positive, finite, dimensionless tolerance requested for the
    kernel's integration.
    """
    _positive("relative_tolerance", relative_tolerance)
    x, y, z = _core._centroid(shape, relative_tolerance)
    return x, y, z


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

    The result unpacks as ``(min, max)``, each corner an (x, y, z) tuple, and
    also provides ``size`` and ``center``.
    """
    # PyO3 converts Rust arrays to lists; expose tuples consistently in Python.
    lower, upper = _core._bounds(shape)
    return Bounds((lower[0], lower[1], lower[2]), (upper[0], upper[1], upper[2]))


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
    """Read a STEP file and merge all of its solids into one shape.

    Part identity is not kept: every solid occurrence is placed in world
    millimetres and united. ``path`` is a string or path object. Reader or
    conversion failures raise ``KernelError``. Filesystem errors propagate
    as ``OSError`` subclasses.
    """
    return _core._import_step(Path(path).read_bytes().decode("latin-1"))
