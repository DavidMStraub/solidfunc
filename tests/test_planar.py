"""Exercise curve topology and its conversion to solid geometry."""

import math

import pytest
import solidfunc as sf


def test_mixed_path_fills_and_extrudes() -> None:
    planar = sf.planar
    arc = planar.arc(center=(0, 0), radius=2, start_angle=0, sweep_angle=180)
    line = planar.line((-2, 0), (2, 0))
    boundary = planar.path([arc, line])

    assert arc.start == (2, 0)
    assert arc.end == pytest.approx((-2, 0))
    assert boundary.is_closed
    assert isinstance(boundary.curves, tuple)
    assert boundary.curves[1].end == (2, 0)

    solid = sf.extrude(planar.profile(boundary), height=1)
    lower, upper = sf.bounds(solid)
    assert lower == pytest.approx((-2, 0, 0))
    assert upper == pytest.approx((2, 2, 1))
    assert sf.volume(solid) == pytest.approx(2 * math.pi)


def test_clockwise_arc_and_open_path() -> None:
    curve = sf.arc(center=(1, 2), radius=3, start_angle=90, sweep_angle=-90)
    assert curve.start == pytest.approx((1, 5))
    assert curve.end == pytest.approx((4, 2))

    outline = sf.path([curve])
    assert not outline.is_closed
    with pytest.raises(ValueError, match="closed"):
        sf.profile(outline)


def test_profile_with_circular_hole() -> None:
    outer = sf.path([sf.circle(radius=4)])
    inner = sf.path([sf.circle(radius=1, center=(1, 0))])

    assert outer.is_closed
    assert outer.curves[0].start == outer.curves[0].end == (4, 0)
    profile = sf.profile(outer, holes=[inner])
    assert sf.volume(sf.extrude(profile, height=3)) == pytest.approx(45 * math.pi)


@pytest.mark.parametrize("center", [(5, 0), (3, 0)])
def test_rejects_hole_outside_or_touching_outer_boundary(center: sf.Point2D) -> None:
    outer = sf.path([sf.circle(radius=4)])
    inner = sf.path([sf.circle(radius=1, center=center)])
    with pytest.raises(ValueError, match="strictly inside"):
        sf.profile(outer, holes=[inner])


def test_rejects_nested_holes() -> None:
    outer = sf.path([sf.circle(radius=4)])
    holes = [sf.path([sf.circle(radius=radius)]) for radius in (2, 1)]
    with pytest.raises(ValueError, match="disjoint"):
        sf.profile(outer, holes=holes)


def test_rejects_empty_and_disconnected_paths() -> None:
    with pytest.raises(ValueError, match="at least one"):
        sf.path([])
    with pytest.raises(ValueError, match="connect"):
        sf.path([sf.line((0, 0), (1, 0)), sf.line((2, 0), (3, 0))])


def test_rejects_coincident_line_endpoints() -> None:
    with pytest.raises(ValueError, match="distinct"):
        sf.line((0, 0), (0, 0))


@pytest.mark.parametrize("sweep", [0, 361, -361, math.inf, math.nan])
def test_rejects_invalid_arc_sweep(sweep: float) -> None:
    with pytest.raises(ValueError, match="sweep"):
        sf.arc(center=(0, 0), radius=1, start_angle=0, sweep_angle=sweep)
