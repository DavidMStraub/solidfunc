"""Sphere, cone, and torus primitives, area, and mass properties."""

import math

import pytest
import solidfunc as sf


def test_sphere_rests_on_z0() -> None:
    ball = sf.sphere(radius=5)
    assert sf.volume(ball) == pytest.approx(4 / 3 * math.pi * 5**3)
    assert sf.area(ball) == pytest.approx(4 * math.pi * 5**2)
    lower, upper = sf.bounds(ball)
    assert lower == pytest.approx((-5, -5, 0), abs=1e-9)
    assert upper == pytest.approx((5, 5, 10))
    assert [face.kind for face in sf.faces(ball)] == ["sphere"]


def test_sphere_accepts_a_diameter() -> None:
    assert sf.volume(sf.sphere(diameter=10)) == pytest.approx(
        sf.volume(sf.sphere(radius=5))
    )


def test_pointed_cone() -> None:
    tip = sf.cone(base_radius=3, top_radius=0, height=4)
    assert sf.volume(tip) == pytest.approx(math.pi * 3**2 * 4 / 3)
    # Base disc plus lateral surface, with slant height 5.
    assert sf.area(tip) == pytest.approx(math.pi * 3 * (3 + 5))
    lower, upper = sf.bounds(tip)
    assert lower == pytest.approx((-3, -3, 0))
    assert upper == pytest.approx((3, 3, 4))
    assert sorted(face.kind for face in sf.faces(tip)) == ["cone", "plane"]


@pytest.mark.parametrize(("base", "top"), [(3, 1), (1, 3)])
def test_frustum_either_way_up(base: float, top: float) -> None:
    frustum = sf.cone(base_diameter=2 * base, top_diameter=2 * top, height=4)
    expected = math.pi * 4 / 3 * (base**2 + base * top + top**2)
    assert sf.volume(frustum) == pytest.approx(expected)


def test_cone_with_equal_ends_points_to_cylinder() -> None:
    with pytest.raises(ValueError, match="cylinder"):
        sf.cone(base_radius=2, top_radius=2, height=1)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"base_radius": 0, "top_radius": 1, "height": 1}, "base_radius"),
        ({"base_radius": 1, "top_radius": -1, "height": 1}, "top_radius"),
        ({"base_radius": 1, "top_radius": math.nan, "height": 1}, "top_radius"),
        ({"base_radius": 1, "top_radius": 0, "height": 0}, "height"),
        ({"base_radius": 1, "base_diameter": 2, "top_radius": 0, "height": 1}, "base_"),
        ({"base_radius": 1, "height": 1}, "top_radius and top_diameter"),
    ],
)
def test_invalid_cone(arguments: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        sf.cone(**arguments)  # type: ignore[call-overload]


def test_torus_rests_on_z0() -> None:
    ring = sf.torus(major_radius=10, minor_radius=2)
    assert sf.volume(ring) == pytest.approx(2 * math.pi**2 * 10 * 2**2)
    assert sf.area(ring) == pytest.approx(4 * math.pi**2 * 10 * 2)
    lower, upper = sf.bounds(ring)
    assert lower == pytest.approx((-12, -12, 0))
    assert upper == pytest.approx((12, 12, 4))
    assert [face.kind for face in sf.faces(ring)] == ["torus"]


@pytest.mark.parametrize(
    ("major", "minor", "message"),
    [
        (2, 2, "smaller"),
        (2, 3, "smaller"),
        (0, 1, "major_radius"),
        (2, -1, "minor_radius"),
    ],
)
def test_invalid_torus(major: float, minor: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        sf.torus(major_radius=major, minor_radius=minor)


def test_new_primitives_combine_with_booleans() -> None:
    block = sf.box(size_x=20, size_y=20, size_z=10)
    dimple = sf.translate(sf.sphere(radius=5), z=5)
    assert sf.volume(block - dimple) == pytest.approx(4000 - 2 / 3 * math.pi * 5**3)


def test_box_area() -> None:
    assert sf.area(sf.box(size_x=10, size_y=20, size_z=30)) == pytest.approx(2200)


def test_centroid_of_a_moved_box() -> None:
    block = sf.translate(sf.box(size_x=10, size_y=20, size_z=30), x=5)
    point = sf.centroid(block)
    assert isinstance(point, tuple)
    assert point == pytest.approx((5, 0, 15), abs=1e-9)


def test_centroid_differs_from_the_bounds_centre() -> None:
    # A pointed cone's centroid lies at a quarter of its height.
    tip = sf.cone(base_radius=3, top_radius=0, height=8)
    assert sf.centroid(tip) == pytest.approx((0, 0, 2), abs=1e-9)
    assert sf.bounds(tip).center == pytest.approx((0, 0, 4))


@pytest.mark.parametrize("function", [sf.area, sf.centroid])
@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf])
def test_invalid_measurement_tolerance(function, value: float) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="relative_tolerance"):
        function(sf.box(size_x=1, size_y=1, size_z=1), relative_tolerance=value)
