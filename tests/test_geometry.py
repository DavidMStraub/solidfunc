"""Exercise the actual kernel through the installed Python package."""

import math
from pathlib import Path

import pytest
import solidfunc as sf


def test_box_geometry() -> None:
    block = sf.box(size_x=10, size_y=20, size_z=30, origin=(1, 2, 3))
    assert type(block) is sf.Shape
    assert sf.volume(block) == pytest.approx(6000)
    assert sf.bounds(block) == ((1, 2, 3), (11, 22, 33))


def test_cylinder_geometry_and_translation() -> None:
    cylinder = sf.cylinder(radius=2.5, height=7, origin=(1, -2, 3))
    moved = sf.translate(cylinder, x=10, y=-5, z=2)

    assert sf.volume(cylinder) == pytest.approx(math.pi * 2.5**2 * 7)
    lower, upper = sf.bounds(cylinder)
    assert lower == pytest.approx((-1.5, -4.5, 3))
    assert upper == pytest.approx((3.5, 0.5, 10))
    moved_lower, moved_upper = sf.bounds(moved)
    assert moved_lower == pytest.approx((8.5, -9.5, 5))
    assert moved_upper == pytest.approx((13.5, -4.5, 12))
    assert sf.volume(moved) == pytest.approx(sf.volume(cylinder))


@pytest.mark.parametrize("dimension", ["radius", "height"])
@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf, -math.inf])
def test_invalid_cylinder_dimensions(dimension: str, value: float) -> None:
    dimensions = {"radius": 2.0, "height": 3.0}
    dimensions[dimension] = value
    with pytest.raises(ValueError, match=dimension):
        sf.cylinder(**dimensions)


def test_invalid_cylinder_origin() -> None:
    with pytest.raises(ValueError, match="cylinder"):
        sf.cylinder(radius=2, height=3, origin=(math.inf, 0, 0))


def test_translation_preserves_input_and_aliases() -> None:
    block = sf.box(size_x=10, size_y=20, size_z=30)
    alias = block
    moved = sf.translate(block, x=100, y=-5, z=2)
    moved_again = sf.translate(moved, x=10)

    assert moved is not block
    assert sf.bounds(alias) == ((0, 0, 0), (10, 20, 30))
    assert sf.bounds(moved) == ((100, -5, 2), (110, 15, 32))
    assert sf.bounds(moved_again) == ((110, -5, 2), (120, 15, 32))
    assert sf.volume(moved) == pytest.approx(sf.volume(block))


@pytest.mark.parametrize("dimension", ["size_x", "size_y", "size_z"])
@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf, -math.inf])
def test_invalid_dimensions(dimension: str, value: float) -> None:
    dimensions = {"size_x": 10.0, "size_y": 20.0, "size_z": 30.0}
    dimensions[dimension] = value
    with pytest.raises(ValueError, match=dimension):
        sf.box(**dimensions)


def test_native_argument_error_preserves_body() -> None:
    block = sf.box(size_x=10, size_y=20, size_z=30)
    with pytest.raises(ValueError, match="translate"):
        sf.translate(block, x=math.nan)
    assert sf.bounds(block) == ((0, 0, 0), (10, 20, 30))


def test_rotation_about_offset_axis_preserves_shape() -> None:
    block = sf.box(size_x=4, size_y=2, size_z=1, origin=(1, 2, 3))
    rotated = sf.rotate(
        block, axis_direction=(0, 0, 2), angle_deg=90, axis_origin=(1, 2, 3)
    )

    lower, upper = sf.bounds(rotated)
    assert lower == pytest.approx((-1, 2, 3))
    assert upper == pytest.approx((1, 6, 4))
    assert sf.volume(rotated) == pytest.approx(sf.volume(block))
    assert sf.bounds(block) == ((1, 2, 3), (5, 4, 4))


@pytest.mark.parametrize(
    ("axis", "angle", "origin"),
    [
        ((0, 0, 0), 90, (0, 0, 0)),
        ((0, 0, math.inf), 90, (0, 0, 0)),
        ((0, 0, 1), math.nan, (0, 0, 0)),
        ((0, 0, 1), 90, (0, math.inf, 0)),
    ],
)
def test_invalid_rotation(axis: sf.Point3D, angle: float, origin: sf.Point3D) -> None:
    block = sf.box(size_x=1, size_y=1, size_z=1)
    with pytest.raises(ValueError, match="rotate"):
        sf.rotate(block, axis_direction=axis, angle_deg=angle, axis_origin=origin)


def test_polygon_extrusion_preserves_reusable_profile(tmp_path: Path) -> None:
    # A clockwise concave outline with an explicit closing vertex.
    points = [(0, 0), (0, 4), (2, 4), (2, 1), (5, 1), (5, 0), (0, 0)]
    profile = sf.polygon(iter(points))
    assert type(profile) is sf.Profile
    points.clear()

    above = sf.extrude(profile, distance=2)
    below = sf.extrude(profile, distance=-3)
    assert sf.bounds(above) == ((0, 0, 0), (5, 4, 2))
    assert sf.bounds(below) == ((0, 0, -3), (5, 4, 0))
    assert sf.volume(above) == pytest.approx(22)
    assert sf.volume(below) == pytest.approx(33)

    path = tmp_path / "extrusion.step"
    sf.export_step(above, path)
    assert "MANIFOLD_SOLID_BREP" in path.read_text()


@pytest.mark.parametrize(
    "points",
    [
        [(0, 0), (1, 0)],
        [(0, 0), (1, 0), (2, 0)],
        [(0, 0), (1, 0), (1, math.inf)],
        [(0, 0), (1, 0), (1, 0), (0, 1)],
    ],
)
def test_invalid_polygon(points: list[sf.Point2D]) -> None:
    with pytest.raises(ValueError, match="polygon"):
        sf.polygon(points)


@pytest.mark.parametrize("height", [0, math.inf, -math.inf, math.nan])
def test_invalid_extrusion_height(height: float) -> None:
    profile = sf.polygon([(0, 0), (1, 0), (0, 1)])
    with pytest.raises(ValueError, match="distance"):
        sf.extrude(profile, distance=height)
