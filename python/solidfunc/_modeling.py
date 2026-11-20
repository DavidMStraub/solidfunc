"""Build solids from profiles placed in model space."""

from collections.abc import Iterable
from math import radians

from . import _core
from ._api import Point3D
from ._core import Path3D, Profile, Shape
from ._frame import _XY, Plane
from .planar import _require_profile


def revolve(
    profile: Profile,
    *,
    axis_direction: Point3D,
    axis_origin: Point3D = (0.0, 0.0, 0.0),
    angle_deg: float = 360.0,
    plane: Plane = _XY,
) -> Shape:
    """Revolve a single-boundary profile into a capped solid.

    ``plane`` places the profile's local XY coordinates. The axis passes
    through the world point ``axis_origin`` in the direction ``axis_direction`` and must
    lie in the placed profile's plane. ``angle_deg`` is in (0, 360] degrees
    and follows the right-hand rule. The profile must lie on one side
    of the axis, and its boundary may touch the axis.
    """
    _require_profile("revolve", profile)
    return _core._revolve(
        profile,
        (plane.origin, plane.x_dir, plane.y_dir),
        axis_origin,
        axis_direction,
        radians(angle_deg),
    )


def loft(
    sections: Iterable[tuple[Profile, Plane]] | Iterable[Path3D],
    /,
    *,
    degree: int = 1,
) -> Shape:
    """Return a capped solid through successive sections.

    Supply (profile, plane) pairs or closed spatial paths. Profile pairs
    use automatic boundary matching. Spatial paths must already have
    corresponding curves in the same traversal order, with corresponding
    starts. Each section must enclose one planar region without holes.
    ``degree`` is the polynomial degree in the direction through the
    sections (1 to 3).
    Supply at least two sections and more sections than the degree.
    """
    profiles: list[tuple[Profile, tuple[Point3D, Point3D, Point3D]]] = []
    paths: list[Path3D] = []
    for section in sections:
        if isinstance(section, Path3D):
            paths.append(section)
        else:
            profile, plane = section
            _require_profile("loft", profile)
            profiles.append((profile, (plane.origin, plane.x_dir, plane.y_dir)))
    if paths and profiles:
        raise ValueError("loft sections must be all profile-plane pairs or all paths")
    if paths:
        return _core._loft_paths(paths, degree)
    return _core._loft(profiles, degree)


def polyline3d(points: Iterable[Point3D], /) -> Path3D:
    """Join consecutive world-space points with straight segments.

    Supply at least two finite XYZ points in millimetres. Repeat the
    first point at the end to close the path.
    """
    return _core._polyline3d(list(points))


def spline3d(points: Iterable[Point3D], /, *, degree: int = 3) -> Path3D:
    """Interpolate a spatial B-spline through world-space points in millimetres.

    ``degree`` is the requested polynomial degree. Supply more distinct
    interpolation points than the degree, in traversal order.
    """
    return _core._spline(list(points), degree)


def sweep(profile: Profile, path: Path3D, /, *, plane: Plane) -> Shape:
    """Carry a filled profile along a spatial path to form a solid.

    ``plane`` places the section at the start of ``path``, with its normal
    parallel to the starting tangent. The section turns with the path,
    and holes in the profile remain open along it.
    Straight segments meet at mitres at sharp polyline corners. The kernel
    can reject paths whose corners or curvature make the sweep self-intersect.
    """
    _require_profile("sweep", profile)
    return _core._sweep(profile, (plane.origin, plane.x_dir, plane.y_dir), path)
