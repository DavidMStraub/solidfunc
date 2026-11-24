"""Check the watertight export mesh and binary STL output."""

import math
import struct
from collections import Counter
from pathlib import Path

import pytest
import solidfunc as sf


def _edge_use(mesh: sf.ExportMesh) -> Counter[tuple[int, int]]:
    use: Counter[tuple[int, int]] = Counter()
    for a, b, c in mesh.triangles:
        for start, end in ((a, b), (b, c), (c, a)):
            use[(min(start, end), max(start, end))] += 1
    return use


def _signed_volume(mesh: sf.ExportMesh) -> float:
    total = 0.0
    for a, b, c in mesh.triangles:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (
            mesh.vertices[a],
            mesh.vertices[b],
            mesh.vertices[c],
        )
        total += (
            ax * (by * cz - bz * cy)
            + ay * (bz * cx - bx * cz)
            + az * (bx * cy - by * cx)
        )
    return total / 6


def _section(width: float, height: float) -> sf.Profile:
    return sf.profile(sf.rectangle(size_x=width, size_y=height))


def _bodies() -> dict[str, sf.Shape]:
    block = sf.box(size_x=40, size_y=30, size_z=20)
    drilled = block - sf.translate(sf.cylinder(diameter=8, height=30), z=-5)
    rounded = sf.fillet(
        block,
        [e for e in sf.edges(block) if e.line_direction and e.line_direction[2] == 1],
        radius=3,
    )
    lofted = sf.loft(
        [
            (_section(30, 20), sf.Plane(origin=(0, 0, 0))),
            (_section(20, 12), sf.Plane(origin=(5, 0, 25))),
        ]
    )
    cut = sf.union(block, sf.translate(sf.cylinder(radius=6, height=40), x=15)) - (
        sf.translate(sf.box(size_x=10, size_y=10, size_z=10), z=5)
    )
    return {
        "box": block,
        "drilled": drilled,
        "filleted": rounded,
        "lofted": lofted,
        "boolean": cut,
    }


BODIES = _bodies()


@pytest.mark.parametrize("name", sorted(BODIES))
def test_mesh_is_watertight_by_index(name: str) -> None:
    shape = BODIES[name]
    mesh = sf.mesh(shape)
    assert mesh.triangles
    assert all(0 <= i < len(mesh.vertices) for t in mesh.triangles for i in t)
    assert all(len(set(t)) == 3 for t in mesh.triangles)
    assert set(_edge_use(mesh).values()) == {2}
    assert set(i for t in mesh.triangles for i in t) == set(range(len(mesh.vertices)))


@pytest.mark.parametrize("name", sorted(BODIES))
def test_mesh_faces_outward_and_matches_volume(name: str) -> None:
    shape = BODIES[name]
    volume = _signed_volume(sf.mesh(shape))
    assert volume > 0
    assert volume == pytest.approx(sf.volume(shape), rel=2e-3)


def test_box_mesh_is_exact() -> None:
    mesh = sf.mesh(sf.box(size_x=2, size_y=3, size_z=5))
    axes = tuple(zip(*mesh.vertices, strict=True))
    assert tuple(map(min, axes)) == pytest.approx((-1, -1.5, 0))
    assert tuple(map(max, axes)) == pytest.approx((1, 1.5, 5))
    assert _signed_volume(mesh) == pytest.approx(30)


def test_finer_chord_tolerance_adds_triangles() -> None:
    cylinder = sf.cylinder(radius=5, height=10)
    coarse = sf.mesh(cylinder, chord_tolerance=0.5)
    fine = sf.mesh(cylinder, chord_tolerance=0.01)
    assert len(fine.triangles) > len(coarse.triangles)
    assert set(_edge_use(fine).values()) == {2}


def test_max_edge_length_limits_triangle_sides() -> None:
    mesh = sf.mesh(sf.box(size_x=10, size_y=10, size_z=10), max_edge_length=2)
    assert len(mesh.triangles) > 12
    for triangle in mesh.triangles:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            assert (
                math.dist(mesh.vertices[triangle[i]], mesh.vertices[triangle[j]])
                <= 2 * 1.5 + 1e-9
            )


@pytest.mark.parametrize("name", ["chord_tolerance", "max_edge_length"])
@pytest.mark.parametrize("value", [0, -1, math.inf, math.nan])
def test_mesh_requires_positive_finite_options(name: str, value: float) -> None:
    block = sf.box(size_x=1, size_y=1, size_z=1)
    with pytest.raises(ValueError, match=name):
        sf.mesh(block, **{name: value})


@pytest.mark.parametrize("name", sorted(BODIES))
def test_export_stl_round_trip(tmp_path: Path, name: str) -> None:
    shape = BODIES[name]
    path = tmp_path / "part.stl"
    sf.export_stl(shape, path)
    data = path.read_bytes()
    (count,) = struct.unpack_from("<I", data, 80)
    assert len(data) == 84 + 50 * count
    mesh = sf.mesh(shape)
    assert count == len(mesh.triangles)
    volume = 0.0
    for k in range(count):
        values = struct.unpack_from("<12f", data, 84 + 50 * k)
        normal, a, b, c = values[0:3], values[3:6], values[6:9], values[9:12]
        cross = (
            (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]),
            (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]),
            (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]),
        )
        assert sum(n * m for n, m in zip(normal, cross, strict=True)) > 0
        volume += (
            sum(
                p * q
                for p, q in zip(
                    a,
                    (
                        b[1] * c[2] - b[2] * c[1],
                        b[2] * c[0] - b[0] * c[2],
                        b[0] * c[1] - b[1] * c[0],
                    ),
                    strict=True,
                )
            )
            / 6
        )
    assert volume == pytest.approx(sf.volume(shape), rel=2e-3)


def test_export_stl_accepts_string_path_and_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "block.stl"
    path.write_bytes(b"old")
    block = sf.box(size_x=1, size_y=2, size_z=3)
    sf.export_stl(block, str(path))
    data = path.read_bytes()
    assert struct.unpack_from("<I", data, 80) == (len(sf.mesh(block).triangles),)
