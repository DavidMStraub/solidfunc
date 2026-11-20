"""Construct directed curves, connected paths and filled regions in the XY plane.

Curves and paths are boundaries. ``profile()`` fills a closed boundary into a
region, and only regions become solids. Coordinates and radii are in
millimetres. Angles are in degrees.
"""

from collections.abc import Iterable
from math import isfinite, radians
from typing import TypeAlias

from . import _core
from ._api import _positive
from ._core import Curve2D, Path2D, Profile, Shape
from ._frame import _XY, Plane

Point2D: TypeAlias = tuple[float, float]
Boundary: TypeAlias = Curve2D | Path2D

__all__ = [
    "Boundary",
    "Curve2D",
    "Path2D",
    "Point2D",
    "Profile",
    "arc",
    "circle",
    "extrude",
    "line",
    "path",
    "polygon",
    "polyline",
    "profile",
    "rectangle",
]


def line(start: Point2D, end: Point2D, /) -> Curve2D:
    """Return the directed line segment from ``start`` to ``end``.

    Both endpoints are finite (x, y) coordinates in millimetres. Coincident
    endpoints raise ``ValueError``.
    """
    return _core._line(start, end)


def arc(
    *, center: Point2D, radius: float, start_angle_deg: float, sweep_angle_deg: float
) -> Curve2D:
    """Return a directed circular arc in the XY plane.

    ``center`` is the circle's (x, y) center and ``radius`` is its positive
    radius, both in millimetres. ``start_angle_deg`` is measured in degrees
    counterclockwise from +X. ``sweep_angle_deg`` is the signed travel in degrees
    from that starting point. Positive sweeps go counterclockwise, negative
    sweeps go clockwise, and ±360 degrees makes a full circle.

    All parameters must be finite. A zero sweep or a sweep greater than
    one turn in magnitude raises ``ValueError``.
    """
    return _core._arc(
        center, radius, radians(start_angle_deg), radians(sweep_angle_deg)
    )


def circle(*, radius: float, center: Point2D = (0.0, 0.0)) -> Curve2D:
    """Return a closed curve traversed once counterclockwise from its +X point.

    ``center`` is a finite (x, y) point and ``radius`` is positive and finite,
    both in millimetres. Use ``profile(circle(...))`` to fill the circle.
    """
    return arc(center=center, radius=radius, start_angle_deg=0.0, sweep_angle_deg=360.0)


def path(curves: Iterable[Curve2D], /) -> Path2D:
    """Join a nonempty sequence of directed curves in traversal order.

    Each curve's end must be within 1e-7 mm of the next curve's start.
    The same tolerance determines whether the last curve joins the first
    and ``is_closed`` is true. The returned path exposes its curves as a
    tuple. An empty sequence or a gap between neighbors raises ``ValueError``.
    """
    return _core._path(list(curves))


def _closed_path(boundary: Boundary) -> Path2D:
    if isinstance(boundary, Curve2D):
        return path([boundary])
    return boundary


def profile(outer: Boundary, /, *, holes: Iterable[Boundary] = ()) -> Profile:
    """Fill a simple closed boundary in the XY plane and subtract any holes.

    ``outer`` and each entry of ``holes`` is a closed ``Path2D`` or a single
    closed ``Curve2D`` such as a circle. Each hole must lie strictly inside the
    exterior and be disjoint from the other holes. Each boundary can be
    traversed in either direction. Open boundaries, zero-area boundaries, and
    invalid hole placement raise ``ValueError``. The result can be passed to
    ``extrude``, ``revolve``, ``sweep``, and ``loft``.
    """
    return _core._profile(_closed_path(outer), [_closed_path(hole) for hole in holes])


def _vertices(operation: str, points: Iterable[Point2D], minimum: int) -> list[Point2D]:
    vertices = [(float(x), float(y)) for x, y in points]
    if len(vertices) < minimum or not all(isfinite(c) for v in vertices for c in v):
        raise ValueError(f"{operation} requires at least {minimum} finite vertices")
    if any(a == b for a, b in zip(vertices, vertices[1:], strict=False)):
        raise ValueError(f"{operation} has consecutive duplicate vertices")
    return vertices


def polyline(points: Iterable[Point2D], /) -> Path2D:
    """Join consecutive XY points with straight segments.

    Supply at least two finite (x, y) points in millimetres. The path is
    open unless the last point repeats the first. Consecutive duplicate
    points raise ``ValueError``. Use ``polygon`` for an outline that closes
    automatically.
    """
    vertices = _vertices("polyline", points, 2)
    return path(line(a, b) for a, b in zip(vertices, vertices[1:], strict=False))


def polygon(points: Iterable[Point2D], /) -> Path2D:
    """Return the closed straight-edged boundary through the given vertices.

    ``points`` supplies at least three finite (x, y) vertices in millimetres,
    in either clockwise or counterclockwise boundary order. The last vertex
    joins the first automatically. Repeating the first vertex at the end
    is also accepted. Consecutive duplicate vertices and zero-area outlines
    raise ``ValueError``. Use ``profile(polygon(...))`` to fill it.
    """
    vertices = list(points)
    if len(vertices) > 1 and vertices[0] == vertices[-1]:
        vertices.pop()
    vertices = _vertices("polygon", vertices, 3)
    closed = [*vertices, vertices[0]]
    twice_area = sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(closed, closed[1:], strict=False)
    )
    if twice_area == 0:
        raise ValueError("polygon outline has zero area")
    return polyline(closed)


def rectangle(*, size_x: float, size_y: float, center: Point2D = (0.0, 0.0)) -> Path2D:
    """Return the closed boundary of an axis-aligned rectangle in local XY.

    ``size_x`` and ``size_y`` are positive, finite dimensions along X and Y.
    ``center`` is the rectangle's (x, y) center. All coordinates and
    dimensions are in millimetres. The boundary runs counterclockwise from
    the minimum corner. Use ``profile(rectangle(...))`` to fill it.
    """
    _positive("size_x", size_x)
    _positive("size_y", size_y)
    x, y = center
    dx, dy = size_x / 2, size_y / 2
    return polygon(
        [(x - dx, y - dy), (x + dx, y - dy), (x + dx, y + dy), (x - dx, y + dy)]
    )


def _require_profile(operation: str, value: object) -> None:
    if not isinstance(value, Profile):
        hint = (
            " Fill a closed boundary with profile(...) first."
            if isinstance(value, Curve2D | Path2D)
            else ""
        )
        raise TypeError(
            f"{operation} requires a Profile, not {type(value).__name__}.{hint}"
        )


def extrude(profile: Profile, *, distance: float, plane: Plane = _XY) -> Shape:
    """Return a solid by sweeping a filled profile normal to its plane.

    ``plane`` places the profile's local XY coordinates, defaulting to world
    XY. ``distance`` is a finite, nonzero signed distance in millimetres.
    Positive follows the plane normal, and negative goes the other way.
    The original profile remains reusable. Passing a curve or path instead
    of a ``Profile`` raises ``TypeError``.
    """
    _require_profile("extrude", profile)
    return _core._extrude(profile, distance, (plane.origin, plane.x_dir, plane.y_dir))
