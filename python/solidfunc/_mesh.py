"""Renderer-independent display geometry."""

from dataclasses import dataclass

from . import _core
from ._api import Point3D, _positive
from ._core import Shape


@dataclass(frozen=True, slots=True)
class Mesh:
    """Indexed display triangles, normals, and visible CAD edge polylines.

    ``vertices`` are world XYZ points in millimetres. Each ``triangles``
    entry indexes three vertices in outward-facing order. ``normals``
    supplies one normal per vertex. ``edge_polylines`` contains separate
    chains of world XYZ points along visible B-rep edges.
    """

    vertices: tuple[Point3D, ...]
    normals: tuple[Point3D, ...]
    triangles: tuple[tuple[int, int, int], ...]
    edge_polylines: tuple[tuple[Point3D, ...], ...]


def tessellate(shape: Shape, /, *, chord_tolerance: float | None = None) -> Mesh:
    """Approximate a shape for display using SolidCore.

    ``chord_tolerance`` is a positive, finite target deviation from the
    exact geometry in millimetres. The default scales with the bounding
    box diagonal. SolidCore also applies angular and resolution limits.
    The result contains separate triangle and CAD edge geometry.
    """
    if chord_tolerance is not None:
        _positive("chord_tolerance", chord_tolerance)
    points, normals, triangles, edges = _core._tessellate(shape, chord_tolerance)
    return Mesh(
        tuple(points), tuple(normals), tuple(triangles), tuple(map(tuple, edges))
    )
