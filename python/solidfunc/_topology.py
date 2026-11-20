"""Inspect a shape and apply finishing operations to its topology."""

from collections.abc import Iterable

from . import _core
from ._api import _positive
from ._core import Edge, Face, Shape, Vertex


def edges(scope: Shape | Face, /) -> tuple[Edge, ...]:
    """Return read-only edges of a shape or of one face.

    A face query includes outer and hole boundaries and returns each
    edge once, including seams shared by two uses on the same face.

    ``kind`` names how the edge's curve is stored (an ``EdgeKind`` such as
    ``"line"`` or ``"circle"``). ``start`` and ``end`` are the edge's
    endpoints in world millimetres, in the edge's own direction; they are
    equal for a closed edge such as a full circle. Line edges provide
    ``line_direction``, the unit vector from ``start`` to ``end``; its sign
    follows the edge's direction, so test ``abs(d[2]) == 1`` for an edge
    parallel to Z. Axis-aligned directions are exact. Circular edges,
    including arcs, provide ``circle_center`` and ``circle_radius`` in world
    millimetres. Kind-specific attributes are ``None`` for other edges.
    ``length`` is the trimmed edge length in millimetres. References
    belong to this exact shape instance.
    """
    if isinstance(scope, Face):
        return _core._face_edges(scope)
    return _core._edges(scope)


def faces(scope: Shape | Edge, /) -> tuple[Face, ...]:
    """Return read-only faces of a shape or the unique faces incident to an edge.

    ``kind`` names how the face's surface is stored (a ``FaceKind`` such as
    ``"plane"`` or ``"cylinder"``). A round on a straight edge reports
    ``"cylinder"``, and the corner where three rounds meet reports
    ``"sphere"``. Surfaces built by ``revolve``, ``loft``, or ``sweep`` are
    often stored as ``"spline"`` even when their shape is a cone or sphere.
    ``area`` is in square millimetres and ``centroid`` is the area centroid
    in world millimetres. ``planar_normal`` is the outward unit vector for
    a planar face and ``None`` for a nonplanar face. References belong to
    this exact shape instance.
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
