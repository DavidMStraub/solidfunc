"""Exercise curve topology and its conversion to solid geometry."""

import math

import pytest
import solidfunc as sf


def test_mixed_path_fills_and_extrudes() -> None:
    planar = sf.planar
    arc = planar.arc(center=(0, 0), radius=2, start_angle_deg=0, sweep_angle_deg=180)
    line = planar.line((-2, 0), (2, 0))
    boundary = planar.path([arc, line])

    assert arc.start == (2, 0)
    assert arc.end == pytest.approx((-2, 0))
    assert boundary.is_closed
    assert isinstance(boundary.curves, tuple)
    assert boundary.curves[1].end == (2, 0)

    solid = sf.extrude(planar.profile(boundary), distance=1)
    lower, upper = sf.bounds(solid)
    assert lower == pytest.approx((-2, 0, 0))
    assert upper == pytest.approx((2, 2, 1))
    assert sf.volume(solid) == pytest.approx(2 * math.pi)


def test_clockwise_arc_and_open_path() -> None:
    curve = sf.arc(center=(1, 2), radius=3, start_angle_deg=90, sweep_angle_deg=-90)
    assert curve.start == pytest.approx((1, 5))
    assert curve.end == pytest.approx((4, 2))

    outline = sf.path([curve])
    assert not outline.is_closed
    with pytest.raises(ValueError, match="closed"):
        sf.profile(outline)


def test_profile_with_circular_hole() -> None:
    outer = sf.path([sf.circle(radius=4)])
    inner = sf.circle(radius=1, center=(1, 0))

    assert outer.is_closed
    assert outer.curves[0].start == outer.curves[0].end == (4, 0)
    # A closed path and a single closed curve are interchangeable boundaries.
    for boundary in (outer, sf.circle(radius=4)):
        profile = sf.profile(boundary, holes=[inner])
        volume = sf.volume(sf.extrude(profile, distance=3))
        assert volume == pytest.approx(45 * math.pi)


def test_rectangle_and_polygon_holes() -> None:
    hole = sf.rectangle(size_x=2, size_y=2, center=(-3, 0))
    triangle = sf.polygon([(2, -1), (4, -1), (2, 1)])
    plate = sf.profile(
        sf.rectangle(size_x=10, size_y=6), holes=[hole, triangle, sf.circle(radius=1)]
    )
    expected = 10 * 6 - 4 - 2 - math.pi
    assert sf.volume(sf.extrude(plate, distance=2)) == pytest.approx(2 * expected)


def test_polyline_is_open_unless_it_returns_to_its_start() -> None:
    open_path = sf.polyline([(0, 0), (4, 0), (4, 3)])
    assert not open_path.is_closed
    assert [curve.end for curve in open_path.curves] == [(4, 0), (4, 3)]
    with pytest.raises(ValueError, match="closed"):
        sf.profile(open_path)

    closed = sf.polyline([(0, 0), (4, 0), (4, 3), (0, 0)])
    assert closed.is_closed
    assert sf.volume(sf.extrude(sf.profile(closed), distance=1)) == pytest.approx(6)

    with pytest.raises(ValueError, match="polyline"):
        sf.polyline([(0, 0)])
    with pytest.raises(ValueError, match="duplicate"):
        sf.polyline([(0, 0), (0, 0), (1, 0)])


@pytest.mark.parametrize(
    "boundary",
    [sf.circle(radius=1), sf.rectangle(size_x=1, size_y=1)],
    ids=["curve", "path"],
)
def test_solid_operations_require_a_filled_profile(boundary: sf.Boundary) -> None:
    with pytest.raises(TypeError, match=r"Profile.*profile\(\.\.\.\)"):
        sf.extrude(boundary, distance=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="revolve requires a Profile"):
        sf.revolve(boundary, axis_direction=(0, 1, 0))  # type: ignore[arg-type]


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
        sf.arc(center=(0, 0), radius=1, start_angle_deg=0, sweep_angle_deg=sweep)


def test_rectangle_extrudes_to_box_with_same_axis_sizes() -> None:
    outline = sf.planar.rectangle(size_x=3, size_y=7, center=(3.5, 2.5))
    assert outline.is_closed
    assert outline.curves[0].start == (2, -1)
    extruded = sf.extrude(sf.profile(outline), distance=5)
    block = sf.translate(sf.box(size_x=3, size_y=7, size_z=5), x=3.5, y=2.5)
    assert sf.bounds(extruded) == sf.bounds(block) == ((2, -1, 0), (5, 6, 5))
    assert sf.volume(extruded) == pytest.approx(105)

    with pytest.raises(ValueError, match="size_y"):
        sf.rectangle(size_x=3, size_y=0)
