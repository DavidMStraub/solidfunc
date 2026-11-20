"""Exercise placed profiles, topology, and STEP import on working solids."""

from math import pi
from pathlib import Path
from typing import get_args

import pytest
import solidfunc as sf


def test_placed_extrusion_and_stepped_revolve() -> None:
    plane = sf.Plane(origin=(2, 3, 4), x_dir=(2, 0, 0), y_dir=(1, 0, 3))
    assert plane.normal == (0, -1, 0)
    assert plane.point(1, 2, 3) == (3, 0, 6)
    triangle = sf.profile(sf.polygon([(0, 0), (2, 0), (0, 1)]))
    lower, upper = sf.bounds(sf.extrude(triangle, distance=5, plane=plane))
    assert lower == pytest.approx((2, -2, 4))
    assert upper == pytest.approx((4, 3, 5))

    outline = [(0, 0), (9, 0), (9, 64), (2.5, 64), (2.5, 65), (0, 65)]
    profile = sf.profile(sf.polygon(outline))
    cell = sf.revolve(
        profile,
        plane=sf.Plane(y_dir=(0, 0, 1)),
        axis_direction=(0, 0, 1),
    )
    assert sf.bounds(cell) == ((-9, -9, 0), (9, 9, 65))
    assert sf.volume(cell) == pytest.approx(pi * (9**2 * 64 + 2.5**2))


def test_face_plane_and_fillet_from_the_hole_rim() -> None:
    plate = sf.box(size_x=30, size_y=30, size_z=5)
    drilled = plate - sf.translate(sf.cylinder(radius=4, height=7), z=-1)
    assert drilled is not None

    (top,) = [face for face in sf.faces(drilled) if face.planar_normal == (0, 0, 1)]
    frame = sf.Plane.from_face(top)
    assert frame.origin == pytest.approx((0, 0, 5))
    assert frame.normal == (0, 0, 1)

    boundary = sf.edges(top)
    assert sorted(edge.kind for edge in boundary) == [
        "circle",
        "line",
        "line",
        "line",
        "line",
    ]
    (rim,) = [edge for edge in boundary if edge.kind == "circle"]
    assert rim.circle_center == pytest.approx((0, 0, 5))
    assert rim.kind == "circle"
    assert rim.circle_radius == pytest.approx(4)
    assert rim.length == pytest.approx(8 * pi)
    rounded = sf.fillet(drilled, [rim], radius=1)
    drilled_volume = 30 * 30 * 5 - 16 * pi * 5
    assert sf.volume(drilled) == pytest.approx(drilled_volume)
    assert 0 < sf.volume(rounded) < drilled_volume

    with pytest.raises(ValueError, match="belong"):
        sf.fillet(sf.translate(drilled), [rim], radius=1)


def test_round_to_rectangular_loft() -> None:
    circle = sf.profile(sf.circle(radius=25))
    rectangle = sf.profile(sf.rectangle(size_x=60, size_y=40))
    duct = sf.loft(
        [(circle, sf.Plane()), (rectangle, sf.Plane(origin=(0, 0, 80)))],
        degree=1,
    )
    lower, upper = sf.bounds(duct)
    assert lower == pytest.approx((-30, -25, 0))
    assert upper == pytest.approx((30, 25, 80))
    assert sf.volume(duct, relative_tolerance=1e-4) > 0


def test_mitred_polyline_sweep() -> None:
    profile = sf.profile(sf.circle(radius=12))
    path = sf.polyline3d([(0, 0, 0), (30, 0, 0), (30, 30, 0), (60, 30, 0)])
    plane = sf.Plane.from_normal(
        origin=path.point_at(0),
        normal=path.tangent_at(0),
        x_dir=(0, 0, 1),
    )
    elbow = sf.sweep(profile, path, plane=plane)
    lower, upper = sf.bounds(elbow)
    assert lower == pytest.approx((0, -12, -12))
    assert upper == pytest.approx((60, 42, 12))
    assert sf.volume(elbow, relative_tolerance=1e-4) == pytest.approx(90 * 12**2 * pi)
    assert path.point_at(0.5) == (30, 15, 0)
    assert path.tangent_at(0.5) == (0, 1, 0)


def test_spline_path_evaluation_and_spatial_loft() -> None:
    spine = sf.spline3d([(0, 0, 0), (1, 2, 0), (3, 3, 2), (5, 5, 5)])
    assert spine.point_at(0) == (0, 0, 0)
    assert spine.point_at(1) == pytest.approx((5, 5, 5))
    assert sum(component**2 for component in spine.tangent_at(0.5)) == pytest.approx(1)
    with pytest.raises(ValueError, match="parameter"):
        spine.point_at(-1)

    outline = [(2, 0), (0, 1), (-2, 0), (0, -1), (2, 0)]
    sections = [sf.spline3d([(x, y, z) for x, y in outline]) for z in (0, 5)]
    assert all(section.is_closed for section in sections)
    assert sf.volume(sf.loft(sections)) > 0


def test_mirror_and_step_round_trip(tmp_path: Path) -> None:
    original = sf.translate(sf.box(size_x=2, size_y=3, size_z=4), x=3, y=1.5)
    reflected = sf.mirror(original, normal=(1, 0, 0))
    assert sf.bounds(original) == ((2, 0, 0), (4, 3, 4))
    assert sf.bounds(reflected) == ((-4, 0, 0), (-2, 3, 4))
    path = tmp_path / "two-pieces.step"
    sf.export_step(original + reflected, path)

    result = sf.import_step(path)
    assert sf.bounds(result) == ((-4, 0, 0), (4, 3, 4))
    assert sf.volume(result) == pytest.approx(48)

    invalid = tmp_path / "invalid.step"
    invalid.write_text("No STEP data")
    with pytest.raises(sf.KernelError, match="import_step"):
        sf.import_step(invalid)
    with pytest.raises(FileNotFoundError):
        sf.import_step(tmp_path / "missing.step")


def test_hollow_mitred_sweep() -> None:
    outer = sf.path([sf.circle(radius=12)])
    bore = sf.path([sf.circle(radius=8)])
    profile = sf.profile(outer, holes=[bore])
    path = sf.polyline3d([(0, 0, 0), (30, 0, 0), (30, 30, 0), (60, 30, 0)])
    plane = sf.Plane.from_normal(normal=path.tangent_at(0))

    elbow = sf.sweep(profile, path, plane=plane)
    assert sf.volume(elbow, relative_tolerance=1e-4) == pytest.approx(
        90 * (12**2 - 8**2) * pi
    )
    # A plug inside the bore at either end has no shared material.
    for origin in [(0, 0, 0), (59, 30, 0)]:
        plug = sf.rotate(
            sf.cylinder(radius=4, height=1), axis_direction=(0, 1, 0), angle_deg=90
        )
        assert (
            sf.intersection(elbow, sf.translate(plug, x=origin[0], y=origin[1])) is None
        )


def test_straight_sweep_with_multiple_holes() -> None:
    outer = sf.path([sf.circle(radius=6)])
    holes = [sf.path([sf.circle(radius=1, center=(x, 0))]) for x in (-2, 2)]
    profile = sf.profile(outer, holes=holes)
    path = sf.polyline3d([(2, 3, 4), (2, 3, 14)])
    swept = sf.sweep(profile, path, plane=sf.Plane(origin=path.point_at(0)))

    assert sf.volume(swept) == pytest.approx(10 * (6**2 - 2) * pi)
    assert sf.volume(sf.extrude(profile, distance=10)) == pytest.approx(
        sf.volume(swept)
    )


def test_chamfer_uses_equal_setbacks_and_preserves_the_source() -> None:
    block = sf.box(size_x=12, size_y=8, size_z=6)
    edge = next(edge for edge in sf.edges(block) if edge.length == pytest.approx(12))

    beveled = sf.chamfer(block, [edge], setback=2)
    assert sf.volume(beveled) == pytest.approx(12 * 8 * 6 - 12 * 2 * 2 / 2)
    assert sf.volume(block) == pytest.approx(12 * 8 * 6)

    with pytest.raises(ValueError, match="chamfer edges must belong"):
        sf.chamfer(beveled, [edge], setback=1)
    with pytest.raises(ValueError, match="setback"):
        sf.chamfer(block, [edge], setback=0)


def test_topology_traversal() -> None:
    box = sf.box(size_x=2, size_y=3, size_z=4)
    assert len(sf.vertices(box)) == 8
    top = next(face for face in sf.faces(box) if face.planar_normal == (0, 0, 1))
    corners = {vertex.point for vertex in sf.vertices(top)}
    assert corners == {(-1, -1.5, 4), (1, -1.5, 4), (-1, 1.5, 4), (1, 1.5, 4)}
    for edge in sf.edges(top):
        endpoints = {vertex.point for vertex in sf.vertices(edge)}
        assert len(endpoints) == 2 and endpoints <= corners
        adjacent = sf.faces(edge)
        assert len(adjacent) == 2
        assert any(face.planar_normal == (0, 0, 1) for face in adjacent)

    cylinder = sf.cylinder(radius=2, height=4)
    circular = next(edge for edge in sf.edges(cylinder) if edge.kind == "circle")
    assert len(sf.vertices(circular)) == 1
    assert len(sf.faces(circular)) == 2


def test_topology_references_compare_by_entity() -> None:
    block = sf.box(size_x=10, size_y=10, size_z=10)
    top = max(sf.faces(block), key=lambda face: face.centroid[2])
    side = max(sf.faces(block), key=lambda face: face.centroid[0])

    assert sf.faces(block)[0] == sf.faces(block)[0]
    assert all(edge in sf.edges(block) for edge in sf.edges(top))
    assert len(set(sf.edges(top)) | set(sf.edges(side))) == 7
    assert len(set(sf.vertices(block)) | set(sf.vertices(top))) == 8
    assert sf.edges(block)[0] != sf.edges(sf.translate(block))[0]

    # The shared edge is listed twice; it is blended once.
    rounded = sf.fillet(block, [*sf.edges(top), *sf.edges(side)], radius=1)
    assert 0 < sf.volume(rounded) < 1000


def test_place_carries_world_xy_onto_a_face() -> None:
    block = sf.box(size_x=10, size_y=20, size_z=4)
    stud = sf.cylinder(diameter=4, height=3)

    top = max(sf.faces(block), key=lambda face: face.centroid[2])
    on_top = sf.place(stud, sf.Plane.from_face(top).offset(x=3))
    lower, upper = sf.bounds(on_top)
    assert lower == pytest.approx((1, -2, 4))
    assert upper == pytest.approx((5, 2, 7))

    # On a side face, the stud's axis follows the outward normal (+X).
    side = max(sf.faces(block), key=lambda face: face.centroid[0])
    lower, upper = sf.bounds(sf.place(stud, sf.Plane.from_face(side)))
    assert lower == pytest.approx((5, -2, 0))
    assert upper == pytest.approx((8, 2, 4))

    assert sf.volume(block + on_top) == pytest.approx(800 + 12 * pi)
    assert sf.bounds(stud).center == pytest.approx((0, 0, 1.5))


def test_plane_offset_moves_along_its_own_axes() -> None:
    plane = sf.Plane.from_normal(origin=(1, 2, 3), normal=(1, 0, 0), x_dir=(0, 1, 0))
    moved = plane.offset(x=1, y=2, z=3)
    assert moved.origin == pytest.approx((4, 3, 5))
    assert (moved.x_dir, moved.y_dir, moved.normal) == (
        plane.x_dir,
        plane.y_dir,
        plane.normal,
    )


def test_edge_endpoints_and_line_direction() -> None:
    block = sf.box(size_x=10, size_y=10, size_z=4)
    vertical = [
        edge
        for edge in sf.edges(block)
        if edge.line_direction is not None and abs(edge.line_direction[2]) == 1
    ]
    assert len(vertical) == 4
    for edge in vertical:
        assert edge.kind == "line"
        assert edge.start[:2] == edge.end[:2]
        assert {edge.start[2], edge.end[2]} == {0, 4}
        assert {vertex.point for vertex in sf.vertices(edge)} == {edge.start, edge.end}

    rim = next(
        edge
        for edge in sf.edges(sf.cylinder(radius=3, height=2))
        if edge.kind == "circle"
    )
    assert rim.start == rim.end
    assert rim.line_direction is None


def test_face_kind_and_area() -> None:
    block = sf.box(size_x=10, size_y=10, size_z=4)
    assert {face.kind for face in sf.faces(block)} == {"plane"}
    top = max(sf.faces(block), key=lambda face: face.centroid[2])
    assert top.area == pytest.approx(100)

    vertical = [
        e for e in sf.edges(block) if e.line_direction and abs(e.line_direction[2]) == 1
    ]
    rounded = sf.fillet(block, vertical, radius=1)
    rounds = [face for face in sf.faces(rounded) if face.kind == "cylinder"]
    assert len(rounds) == 4
    assert all(face.area == pytest.approx(pi * 1 * 4 / 2) for face in rounds)

    corners = sf.fillet(block, sf.edges(block), radius=1)
    assert sum(face.kind == "sphere" for face in sf.faces(corners)) == 8

    ring = sf.revolve(
        sf.profile(sf.circle(radius=1, center=(4, 0))),
        plane=sf.Plane(y_dir=(0, 0, 1)),
        axis_direction=(0, 0, 1),
    )
    assert [face.kind for face in sf.faces(ring)] == ["torus"]


def test_reported_kinds_match_their_literal_types() -> None:
    block = sf.box(size_x=4, size_y=4, size_z=4)
    shapes = [
        sf.fillet(block, sf.edges(block), radius=0.5),
        sf.cylinder(radius=1, height=1),
        sf.loft(
            [
                (sf.profile(sf.circle(radius=2)), sf.Plane()),
                (
                    sf.profile(sf.rectangle(size_x=4, size_y=3)),
                    sf.Plane(origin=(0, 0, 5)),
                ),
            ]
        ),
    ]
    for shape in shapes:
        assert {face.kind for face in sf.faces(shape)} <= set(get_args(sf.FaceKind))
        assert {edge.kind for edge in sf.edges(shape)} <= set(get_args(sf.EdgeKind))
