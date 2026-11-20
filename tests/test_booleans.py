"""Analytical boolean results, empty sets, and operand preservation."""

from collections.abc import Callable
from operator import add, sub

import pytest
import solidfunc as sf

Boolean = Callable[[sf.Shape, sf.Shape], sf.Shape | None]


@pytest.mark.parametrize(
    ("operation", "expected_volume", "lower", "upper"),
    [
        (sf.union, 36, (-2, -1.5, 0), (4, 1.5, 2)),
        (sf.intersection, 12, (0, -1.5, 0), (2, 1.5, 2)),
        (sf.difference, 12, (-2, -1.5, 0), (0, 1.5, 2)),
        (add, 36, (-2, -1.5, 0), (4, 1.5, 2)),
        (sub, 12, (-2, -1.5, 0), (0, 1.5, 2)),
    ],
)
def test_overlapping_boxes(
    operation: Boolean,
    expected_volume: float,
    lower: sf.Point3D,
    upper: sf.Point3D,
) -> None:
    left = sf.box(size_x=4, size_y=3, size_z=2)
    right = sf.translate(left, x=2)
    left_alias, right_alias = left, right

    result = operation(left, right)

    assert result is not None
    assert result is not left and result is not right
    assert sf.volume(result) == pytest.approx(expected_volume)
    assert sf.bounds(result) == (lower, upper)
    # Editing a later copy must not affect either operand or the result.
    sf.translate(result, x=100)
    assert sf.bounds(result) == (lower, upper)
    assert sf.bounds(left_alias) == ((-2, -1.5, 0), (2, 1.5, 2))
    assert sf.bounds(right_alias) == ((0, -1.5, 0), (4, 1.5, 2))
    assert sf.volume(left_alias) == pytest.approx(24)
    assert sf.volume(right_alias) == pytest.approx(24)


@pytest.mark.parametrize(
    "operation", [sf.union, sf.intersection, sf.difference, add, sub]
)
def test_same_operand(operation: Boolean) -> None:
    block = sf.box(size_x=4, size_y=3, size_z=2)
    result = operation(block, block)

    if operation in (sf.difference, sub):
        assert result is None
    else:
        assert result is not None and result is not block
        assert sf.volume(result) == pytest.approx(24)
        assert sf.bounds(result) == ((-2, -1.5, 0), (2, 1.5, 2))
    assert sf.volume(block) == pytest.approx(24)
    assert sf.bounds(block) == ((-2, -1.5, 0), (2, 1.5, 2))


def test_chained_operators() -> None:
    block = sf.box(size_x=4, size_y=3, size_z=2)
    shifted = sf.translate(block, x=2)
    result = (block + shifted) - shifted

    assert result is not None
    assert sf.volume(result) == pytest.approx(12)
    assert sf.bounds(result) == ((-2, -1.5, 0), (0, 1.5, 2))
    assert sf.volume(block) == pytest.approx(24)
    assert sf.volume(shifted) == pytest.approx(24)


@pytest.mark.parametrize("operation", [add, sub])
def test_operators_reject_unsupported_operands(
    operation: Callable[..., object],
) -> None:
    block = sf.box(size_x=4, size_y=3, size_z=2)
    with pytest.raises(TypeError, match="unsupported operand"):
        operation(block, object())
    with pytest.raises(TypeError, match="unsupported operand"):
        operation(object(), block)
    assert sf.volume(block) == pytest.approx(24)


def test_augmented_addition_preserves_alias() -> None:
    block = sf.box(size_x=4, size_y=3, size_z=2)
    alias = block
    block += sf.translate(block, x=2)

    assert block is not alias
    assert sf.volume(block) == pytest.approx(36)
    assert sf.volume(alias) == pytest.approx(24)


def test_disjoint_operands() -> None:
    left = sf.box(size_x=4, size_y=3, size_z=2)
    right = sf.translate(left, x=10)

    combined = sf.union(left, right)
    assert sf.volume(combined) == pytest.approx(48)
    assert sf.bounds(combined) == ((-2, -1.5, 0), (12, 1.5, 2))
    assert sf.intersection(left, right) is None
    remaining = sf.difference(left, right)
    assert remaining is not None and remaining is not left
    assert sf.volume(remaining) == pytest.approx(24)
    assert sf.bounds(remaining) == sf.bounds(left)


def test_containment_and_difference_order() -> None:
    outer = sf.box(size_x=10, size_y=10, size_z=10)
    inner = sf.translate(sf.box(size_x=2, size_y=2, size_z=2), z=4)

    cavity = sf.difference(outer, inner)
    assert cavity is not None
    assert sf.volume(cavity) == pytest.approx(992)
    assert sf.difference(inner, outer) is None
    assert sf.volume(outer) == pytest.approx(1000)
    assert sf.volume(inner) == pytest.approx(8)


def test_difference_can_split_a_solid() -> None:
    block = sf.box(size_x=6, size_y=2, size_z=2)
    cutter = sf.translate(sf.box(size_x=2, size_y=4, size_z=4), z=-1)
    result = sf.difference(block, cutter)

    assert result is not None
    assert sf.volume(result) == pytest.approx(16)
    assert sf.bounds(result) == ((-3, -1, 0), (3, 1, 2))
