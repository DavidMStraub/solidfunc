"""Renderer-independent display geometry and export meshes."""

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


@dataclass(frozen=True, slots=True)
class ExportMesh:
    """Indexed triangles of a closed solid, with vertices shared between faces.

    ``vertices`` are world XYZ points in millimetres. Each ``triangles`` entry
    indexes three vertices in counter-clockwise order seen from outside the
    solid. A point on an edge or corner of the solid is one vertex however
    many faces meet there, so every edge of the mesh is used by exactly two
    triangles.
    """

    vertices: tuple[Point3D, ...]
    triangles: tuple[tuple[int, int, int], ...]


def mesh(
    shape: Shape,
    /,
    *,
    chord_tolerance: float | None = None,
    max_edge_length: float | None = None,
) -> ExportMesh:
    """Mesh a shape for export, with faces joined at shared vertices.

    Unlike ``tessellate``, which is a display mesh, this uses SolidCore's mesh
    path, meant for mesh export and analysis. It is slower. ``chord_tolerance``
    is a positive, finite target deviation from the exact geometry in
    millimetres and defaults to 1/5000 of the bounding box diagonal.
    ``max_edge_length`` is an optional positive, finite longest triangle side
    in millimetres; by default curvature and ``chord_tolerance`` decide.
    A face the kernel cannot mesh raises ``KernelError``, so a returned mesh is
    closed; the kernel may still leave a face short of the requested triangle
    shape or chord tolerance, which is not reported.
    """
    if chord_tolerance is not None:
        _positive("chord_tolerance", chord_tolerance)
    if max_edge_length is not None:
        _positive("max_edge_length", max_edge_length)
    points, triangles = _core._mesh(shape, chord_tolerance, max_edge_length)
    return ExportMesh(tuple(points), tuple(triangles))
