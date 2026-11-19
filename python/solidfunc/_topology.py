"""Inspect a shape and apply finishing operations to its topology."""

from collections.abc import Iterable

from . import _core
from ._api import Point3D, _positive
from ._core import Edge, Face, Shape, Vertex
from ._frame import Plane


def edges(scope: Shape | Face, /) -> tuple[Edge, ...]:
    """Return read-only edges of a shape or of one face.

    A face query includes outer and hole boundaries and returns each
    edge once, including seams shared by two uses on the same face.

    ``kind`` names the underlying curve (for example, ``"line"`` or
    ``"circle"``). Circular edges, including arcs, provide
    ``circle_center`` and ``circle_radius`` in world millimetres.
    Other edges return ``None`` for these attributes. ``length`` is the
    trimmed edge length in millimetres. References belong to this
    exact shape instance.
    """
    if isinstance(scope, Face):
        return _core._face_edges(scope)
    return _core._edges(scope)


def faces(scope: Shape | Edge, /) -> tuple[Face, ...]:
    """Return read-only faces of a shape or the unique faces incident to an edge.

    ``center`` is the area centroid in world millimetres. ``normal``
    is the outward unit vector for a planar face and ``None`` for a
    nonplanar face. References belong to this exact shape instance.
    """
    if isinstance(scope, Edge):
        return _core._edge_faces(scope)
    return _core._faces(scope)


def vertices(scope: Shape | Face | Edge, /) -> tuple[Vertex, ...]:
    """Return unique topological vertices in the given scope.

    A face includes vertices on hole boundaries. A closed edge whose
    endpoints share one vertex returns it once. Each vertex exposes its
    world XYZ coordinates in millimetres via ``point``.
    """
    if isinstance(scope, Face):
        return _core._face_vertices(scope)
    if isinstance(scope, Edge):
        return _core._edge_vertices(scope)
    return _core._vertices(scope)


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


def chamfer(shape: Shape, edges: Iterable[Edge], /, *, setback: float) -> Shape:
    """Bevel the selected edges of a copy using equal setbacks.

    ``edges`` must contain distinct references from this exact ``shape``.
    ``setback`` is the setback along each adjacent face in millimetres.
    It must be positive and finite. The kernel may refuse a setback that
    does not fit the geometry.
    """
    _positive("setback", setback)
    return _core._chamfer(shape, list(edges), setback)
