"""Check native display mesh geometry without requiring a viewer."""

import math

import pytest
import solidfunc as sf


def test_tessellate_preserves_cad_edge_outlines() -> None:
    block = sf.box(size_x=2, size_y=3, size_z=5, origin=(1, 2, 3))
    mesh = sf.tessellate(block)
    assert mesh.triangles
    assert len(mesh.vertices) == len(mesh.normals)
    assert all(
        0 <= index < len(mesh.vertices)
        for triangle in mesh.triangles
        for index in triangle
    )
    assert all(math.isclose(math.hypot(*normal), 1) for normal in mesh.normals)
    axes = tuple(zip(*mesh.vertices, strict=True))
    assert tuple(map(min, axes)) == pytest.approx((1, 2, 3))
    assert tuple(map(max, axes)) == pytest.approx((3, 5, 8))
    assert len(mesh.edge_polylines) == 12
    assert all(len(edge) >= 2 for edge in mesh.edge_polylines)
    assert sf.volume(block) == pytest.approx(30)


@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan])
def test_tessellate_requires_positive_finite_chord_tolerance(value: float) -> None:
    block = sf.box(size_x=1, size_y=1, size_z=1)
    with pytest.raises(ValueError, match="chord_tolerance"):
        sf.tessellate(block, chord_tolerance=value)
