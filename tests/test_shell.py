"""Hollowing solids with shell()."""

import math

import pytest
import solidfunc as sf


def _cube_and_top() -> tuple[sf.Shape, sf.Face]:
    cube = sf.box(size_x=20, size_y=20, size_z=20)
    top = max(sf.faces(cube), key=lambda face: face.centroid[2])
    return cube, top


def test_inward_shell_keeps_the_outer_size() -> None:
    cube, top = _cube_and_top()
    cup = sf.shell(cube, [top], thickness=2)
    assert sf.volume(cup) == pytest.approx(20**3 - 16 * 16 * 18)
    assert sf.bounds(cup) == sf.bounds(cube)
    assert sf.volume(cube) == pytest.approx(20**3)


def test_outward_shell_grows_with_sharp_corners() -> None:
    cube, top = _cube_and_top()
    cup = sf.shell(cube, [top], thickness=2, side="outward")
    assert sf.volume(cup) == pytest.approx(24 * 24 * 22 - 20**3)
    lower, upper = sf.bounds(cup)
    assert lower == pytest.approx((-12, -12, -2))
    assert upper == pytest.approx((12, 12, 20))


def test_shell_without_open_faces_leaves_an_inner_void() -> None:
    cube, _ = _cube_and_top()
    hollow = sf.shell(cube, [], thickness=2)
    assert sf.volume(hollow) == pytest.approx(20**3 - 16**3)
    assert sf.area(hollow) == pytest.approx(6 * 20**2 + 6 * 16**2)


def test_shell_of_a_curved_solid() -> None:
    can = sf.cylinder(radius=10, height=20)
    top = max(sf.faces(can), key=lambda face: face.centroid[2])
    cup = sf.shell(can, [top], thickness=1)
    expected = math.pi * (10**2 * 20 - 9**2 * 19)
    assert sf.volume(cup) == pytest.approx(expected)


def test_repeated_open_faces_count_once() -> None:
    cube, top = _cube_and_top()
    assert sf.volume(sf.shell(cube, [top, top], thickness=2)) == pytest.approx(
        sf.volume(sf.shell(cube, [top], thickness=2))
    )


def test_faces_must_belong_to_the_shape() -> None:
    cube, top = _cube_and_top()
    with pytest.raises(ValueError, match="belong"):
        sf.shell(sf.translate(cube), [top], thickness=1)


def test_a_wall_that_does_not_fit_raises() -> None:
    cube, top = _cube_and_top()
    with pytest.raises(sf.KernelError, match="shell"):
        sf.shell(cube, [top], thickness=11)


@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf])
def test_invalid_thickness(value: float) -> None:
    cube, top = _cube_and_top()
    with pytest.raises(ValueError, match="thickness"):
        sf.shell(cube, [top], thickness=value)


def test_invalid_side() -> None:
    cube, top = _cube_and_top()
    with pytest.raises(ValueError, match="side"):
        sf.shell(cube, [top], thickness=1, side="both")  # type: ignore[arg-type]
