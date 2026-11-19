"""Check exchange with an independent kernel when CadQuery is available."""

import math
from pathlib import Path

import pytest
import solidfunc as sf


@pytest.mark.parametrize(
    "operation",
    ["cylinder", "union", "intersection", "difference", "disjoint_union", "split"],
)
def test_cylinder_and_boolean_step_round_trip(tmp_path: Path, operation: str) -> None:
    cq = pytest.importorskip("cadquery")
    cylinder = sf.cylinder(radius=2, height=12, origin=(5, 5, -1))
    block = sf.box(size_x=10, size_y=10, size_z=10)
    solid_count = 1
    if operation == "cylinder":
        result = cylinder
        expected_volume = math.pi * 4 * 12
    elif operation == "union":
        result = sf.union(block, cylinder)
        expected_volume = 1000 + math.pi * 4 * 2
    elif operation == "intersection":
        result = sf.intersection(block, cylinder)
        expected_volume = math.pi * 4 * 10
    elif operation == "difference":
        result = sf.difference(block, cylinder)
        expected_volume = 1000 - math.pi * 4 * 10
    elif operation == "disjoint_union":
        result = sf.union(block, sf.translate(block, x=20))
        expected_volume = 2000
        solid_count = 2
    else:
        cutter = sf.box(size_x=2, size_y=12, size_z=12, origin=(4, -1, -1))
        result = sf.difference(block, cutter)
        expected_volume = 800
        solid_count = 2
    assert result is not None
    path = tmp_path / f"{operation}.step"

    sf.export_step(result, path, name=operation)
    imported = cq.importers.importStep(str(path)).val()

    assert imported.isValid()
    assert len(imported.Solids()) == solid_count
    assert sf.volume(result) == pytest.approx(expected_volume, rel=1e-9)
    assert imported.Volume() == pytest.approx(expected_volume, rel=1e-9)
    lower, upper = sf.bounds(result)
    bounds = imported.BoundingBox()
    assert (bounds.xmin, bounds.ymin, bounds.zmin) == pytest.approx(lower, abs=1e-6)
    assert (bounds.xmax, bounds.ymax, bounds.zmax) == pytest.approx(upper, abs=1e-6)
    assert sf.volume(block) == pytest.approx(1000)
    assert sf.volume(cylinder) == pytest.approx(math.pi * 4 * 12)


@pytest.mark.parametrize("as_string", [False, True])
def test_step_round_trip(tmp_path: Path, as_string: bool) -> None:
    cq = pytest.importorskip("cadquery")
    original = sf.box(size_x=10, size_y=20, size_z=30, origin=(1, 2, 3))
    block = sf.translate(original, x=100, y=-5, z=2)
    path = tmp_path / "block.step"

    sf.export_step(block, str(path) if as_string else path, name="Block")
    imported = cq.importers.importStep(str(path)).val()

    assert imported.isValid()
    assert len(imported.Solids()) == 1
    assert imported.Volume() == pytest.approx(sf.volume(block), rel=1e-9)
    lower, upper = sf.bounds(block)
    bounds = imported.BoundingBox()
    assert (bounds.xmin, bounds.ymin, bounds.zmin) == pytest.approx(lower)
    assert (bounds.xmax, bounds.ymax, bounds.zmax) == pytest.approx(upper)
    assert sf.bounds(original) == ((1, 2, 3), (11, 22, 33))


def test_step_file_and_input_preservation(tmp_path: Path) -> None:
    block = sf.box(size_x=10, size_y=20, size_z=30)
    path = tmp_path / "block.step"
    sf.export_step(block, path, name="Block")

    text = path.read_text(encoding="utf-8")
    assert text.startswith("ISO-10303-21;")
    assert text.rstrip().endswith("END-ISO-10303-21;")
    assert "MANIFOLD_SOLID_BREP('Block'" in text
    assert sf.bounds(block) == ((0, 0, 0), (10, 20, 30))
    assert sf.volume(block) == pytest.approx(6000)


def test_step_io_error(tmp_path: Path) -> None:
    block = sf.box(size_x=1, size_y=2, size_z=3)
    with pytest.raises(FileNotFoundError):
        sf.export_step(block, tmp_path / "missing" / "block.step")
