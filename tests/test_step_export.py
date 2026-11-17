"""Check exchange with an independent kernel when CadQuery is available."""

from pathlib import Path

import pytest
import solidfunc as sf


@pytest.mark.parametrize("as_string", [False, True])
def test_step_round_trip(tmp_path: Path, as_string: bool) -> None:
    cq = pytest.importorskip("cadquery")
    original = sf.box(length=10, width=20, height=30, origin=(1, 2, 3))
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
    block = sf.box(length=10, width=20, height=30)
    path = tmp_path / "block.step"
    sf.export_step(block, path, name="Block")

    text = path.read_text(encoding="utf-8")
    assert text.startswith("ISO-10303-21;")
    assert text.rstrip().endswith("END-ISO-10303-21;")
    assert "MANIFOLD_SOLID_BREP('Block'" in text
    assert sf.bounds(block) == ((0, 0, 0), (10, 20, 30))
    assert sf.volume(block) == pytest.approx(6000)


def test_step_io_error(tmp_path: Path) -> None:
    block = sf.box(length=1, width=2, height=3)
    with pytest.raises(FileNotFoundError):
        sf.export_step(block, tmp_path / "missing" / "block.step")
