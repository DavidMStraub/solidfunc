"""Exercise placed profiles, topology, and STEP import on working solids."""

from math import pi
from pathlib import Path

import pytest
import solidfunc as sf


def test_placed_extrusion_and_stepped_revolve() -> None:
    plane = sf.Plane(origin=(2, 3, 4), x_dir=(2, 0, 0), y_dir=(1, 0, 3))
    assert plane.normal == (0, -1, 0)
    assert plane.point(1, 2, 3) == (3, 0, 6)
    triangle = sf.polygon([(0, 0), (2, 0), (0, 1)])
    lower, upper = sf.bounds(sf.extrude(triangle, height=5, plane=plane))
    assert lower == pytest.approx((2, -2, 4))
    assert upper == pytest.approx((4, 3, 5))

    profile = sf.polygon([(0, 0), (9, 0), (9, 64), (2.5, 64), (2.5, 65), (0, 65)])
    cell = sf.revolve(
        profile,
        plane=sf.Plane(y_dir=(0, 0, 1)),
        axis=(0, 0, 1),
    )
    assert sf.bounds(cell) == ((-9, -9, 0), (9, 9, 65))
    assert sf.volume(cell) == pytest.approx(pi * (9**2 * 64 + 2.5**2))


def test_face_plane_and_fillet_from_the_hole_rim() -> None:
    plate = sf.box(length=30, width=30, height=5)
    drilled = plate - sf.cylinder(radius=4, height=7, origin=(15, 15, -1))
    assert drilled is not None

    (top,) = [face for face in sf.faces(drilled) if face.normal == (0, 0, 1)]
    frame = sf.face_plane(top)
    assert frame.origin == pytest.approx((15, 15, 5))
    assert frame.normal == (0, 0, 1)

    (rim,) = [
        edge
        for edge in sf.edges(drilled)
        if edge.circle_center == pytest.approx((15, 15, 5))
    ]
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
    circle = sf.profile(sf.path([sf.circle(radius=25)]))
    rectangle = sf.polygon([(-30, -20), (30, -20), (30, 20), (-30, 20)])
    duct = sf.loft([(circle, sf.Plane()), (rectangle, sf.Plane(origin=(0, 0, 80)))])
    lower, upper = sf.bounds(duct)
    assert lower == pytest.approx((-30, -25, 0))
    assert upper == pytest.approx((30, 25, 80))
    assert sf.volume(duct, relative_accuracy=1e-4) > 0


def test_mitred_polyline_sweep() -> None:
    profile = sf.profile(sf.path([sf.circle(radius=12)]))
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
    assert sf.volume(elbow, relative_accuracy=1e-4) == pytest.approx(90 * 12**2 * pi)
    assert path.point_at(0.5) == (30, 15, 0)
    assert path.tangent_at(0.5) == (0, 1, 0)


def test_spline_path_evaluation_and_spatial_loft() -> None:
    spine = sf.spline([(0, 0, 0), (1, 2, 0), (3, 3, 2), (5, 5, 5)])
    assert spine.point_at(0) == (0, 0, 0)
    assert spine.point_at(1) == pytest.approx((5, 5, 5))
    assert sum(component**2 for component in spine.tangent_at(0.5)) == pytest.approx(1)
    with pytest.raises(ValueError, match="parameter"):
        spine.point_at(-1)

    outline = [(2, 0), (0, 1), (-2, 0), (0, -1), (2, 0)]
    sections = [sf.spline([(x, y, z) for x, y in outline]) for z in (0, 5)]
    assert all(section.is_closed for section in sections)
    assert sf.volume(sf.loft(sections)) > 0


def test_mirror_and_step_round_trip(tmp_path: Path) -> None:
    original = sf.box(length=2, width=3, height=4, origin=(2, 0, 0))
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
