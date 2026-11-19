"""Construct directed curves, connected paths and filled regions in the XY plane.

Coordinates and radii are in millimetres. Angles are in degrees.
"""

from collections.abc import Iterable
from math import radians
from typing import TypeAlias

from . import _core
from ._api import _positive
from ._core import Curve2D, Path2D, Profile, Shape
from ._frame import _XY, Plane

Point2D: TypeAlias = tuple[float, float]

__all__ = [
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
    both in millimetres. Use ``profile(path([curve]))`` to fill the circle.
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


def profile(outer: Path2D, /, *, holes: Iterable[Path2D] = ()) -> Profile:
    """Fill a simple closed path in the XY plane and subtract any holes.

    ``outer`` is the exterior boundary. Each path in ``holes`` must be closed,
    lie strictly inside the exterior, and be disjoint from the other holes.
    Each boundary can be traversed in either direction. Open boundaries,
    zero-area boundaries, and invalid hole placement raise ``ValueError``.
    The result can be passed to ``extrude``.
    """
    return _core._profile(outer, list(holes))


def polygon(points: Iterable[Point2D], /) -> Profile:
    """Return a filled XY profile bounded by a simple polygon.

    ``points`` supplies at least three finite (x, y) vertices in millimetres,
    in either clockwise or counterclockwise boundary order. The last vertex
    joins the first automatically. Repeating the first vertex at the end
    is also accepted. Consecutive duplicate vertices and zero-area outlines
    raise ``ValueError``.
    """
    return _core._polygon(list(points))


def rectangle(*, size_x: float, size_y: float, origin: Point2D = (0.0, 0.0)) -> Profile:
    """Return a filled axis-aligned rectangle in the local XY plane.

    ``size_x`` and ``size_y`` are positive, finite dimensions along X and Y.
    ``origin`` is the (x, y) corner with the minimum coordinates.
    All coordinates and dimensions are in millimetres.
    """
    _positive("size_x", size_x)
    _positive("size_y", size_y)
    x, y = origin
    return polygon([(x, y), (x + size_x, y), (x + size_x, y + size_y), (x, y + size_y)])


def extrude(profile: Profile, *, distance: float, plane: Plane = _XY) -> Shape:
    """Return a solid by sweeping a filled profile normal to its plane.

    ``plane`` places the profile's local XY coordinates, defaulting to world
    XY. ``distance`` is a finite, nonzero signed distance in millimetres.
    Positive follows the plane normal, and negative goes the other way.
    The original profile remains reusable.
    """
    return _core._extrude(profile, distance, (plane.origin, plane.x_dir, plane.y_dir))
