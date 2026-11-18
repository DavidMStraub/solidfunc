"""Exercise the actual kernel through the installed Python package."""

import math

import pytest
import solidfunc as sf


def test_box_geometry() -> None:
    block = sf.box(length=10, width=20, height=30, origin=(1, 2, 3))
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
    block = sf.box(length=10, width=20, height=30)
    alias = block
    moved = sf.translate(block, x=100, y=-5, z=2)
    moved_again = sf.translate(moved, x=10)

    assert moved is not block
    assert sf.bounds(alias) == ((0, 0, 0), (10, 20, 30))
    assert sf.bounds(moved) == ((100, -5, 2), (110, 15, 32))
    assert sf.bounds(moved_again) == ((110, -5, 2), (120, 15, 32))
    assert sf.volume(moved) == pytest.approx(sf.volume(block))


@pytest.mark.parametrize("dimension", ["length", "width", "height"])
@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf, -math.inf])
def test_invalid_dimensions(dimension: str, value: float) -> None:
    dimensions = {"length": 10.0, "width": 20.0, "height": 30.0}
    dimensions[dimension] = value
    with pytest.raises(ValueError, match=dimension):
        sf.box(**dimensions)


def test_native_argument_error_preserves_body() -> None:
    block = sf.box(length=10, width=20, height=30)
    with pytest.raises(ValueError, match="translate"):
        sf.translate(block, x=math.nan)
    assert sf.bounds(block) == ((0, 0, 0), (10, 20, 30))
