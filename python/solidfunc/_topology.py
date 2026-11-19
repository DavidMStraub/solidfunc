"""Inspect a shape and apply finishing operations to its topology."""

from collections.abc import Iterable

from . import _core
from ._api import Point3D, _positive
from ._core import Edge, Face, Shape
from ._frame import Plane


def edges(shape: Shape, /) -> tuple[Edge, ...]:
    """Return the shape's edges as read-only references.

    ``kind`` names the underlying curve (for example, ``"line"`` or
    ``"circle"``). Circular edges, including arcs, provide
    ``circle_center`` and ``circle_radius`` in world millimetres.
    Other edges return ``None`` for these attributes. ``length`` is the
    trimmed edge length in millimetres. References belong to this
    exact shape instance.
    """
    return _core._edges(shape)


def faces(shape: Shape, /) -> tuple[Face, ...]:
    """Return the shape's faces as read-only references.

    ``center`` is the area centroid in world millimetres. ``normal``
    is the outward unit vector for a planar face and ``None`` for a
    nonplanar face. References belong to this exact shape instance.
    """
    return _core._faces(shape)


def face_plane(face: Face, /, *, x_dir: Point3D | None = None) -> Plane:
    """Return a placement frame at a planar face's centroid.

    The frame normal points outward. The world direction ``x_dir``
    is projected onto the face to orient the frame. If omitted, the
    world axis least aligned with the normal supplies this direction.
    Nonplanar faces and directions parallel to the normal raise
    ``ValueError``.
    """
    normal = face.normal
    if normal is None:
        raise ValueError("face_plane requires a planar face")
    return Plane.from_normal(origin=face.center, normal=normal, x_dir=x_dir)


def fillet(shape: Shape, edges: Iterable[Edge], /, *, radius: float) -> Shape:
    """Round the selected edges of a copy using a constant radius.

    ``edges`` must contain distinct references obtained from this
    exact ``shape``. ``radius`` is positive, finite, and in millimetres.
    The kernel may refuse a radius that does not fit the geometry.
    """
    _positive("radius", radius)
    return _core._fillet(shape, list(edges), radius)
