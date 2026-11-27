"""solidfunc as a producer and a consumer of the __cad_interface__ protocol."""

import math
from pathlib import Path
from typing import Any

import pytest
import solidfunc as sf


def _part() -> sf.Shape:
    return sf.box(size_x=10, size_y=10, size_z=10) - sf.cylinder(radius=2, height=10)


EXPECTED_VOLUME = 1000 - math.pi * 4 * 10


def test_without_accept_returns_step() -> None:
    result = _part().__cad_interface__()
    assert result["version"] == 1
    assert result["type"] == "shape"
    assert result["format"] == "step"
    assert isinstance(result["data"], bytes)
    assert result["data"].startswith(b"ISO-10303-21;")


def test_skips_formats_it_does_not_offer() -> None:
    result = _part().__cad_interface__(accept=["ocp", "brep_binary", "x-new", "step"])
    assert result["format"] == "step"


def test_rejects_when_step_is_not_accepted() -> None:
    with pytest.raises(ValueError, match="only the 'step' format"):
        _part().__cad_interface__(accept=["ocp", "brep_text"])


def test_rejects_a_bare_string() -> None:
    with pytest.raises(TypeError, match="sequence"):
        _part().__cad_interface__(accept="step")  # type: ignore[arg-type]


def test_accept_is_keyword_only() -> None:
    with pytest.raises(TypeError):
        _part().__cad_interface__(["step"])  # type: ignore[misc]


def test_step_bytes_read_back(tmp_path: Path) -> None:
    path = tmp_path / "part.step"
    path.write_bytes(_part().__cad_interface__(accept=["step"])["data"])
    assert sf.volume(sf.import_step(path)) == pytest.approx(EXPECTED_VOLUME)


def test_an_opencascade_consumer_reads_the_bytes(tmp_path: Path) -> None:
    cq = pytest.importorskip("cadquery")
    path = tmp_path / "part.step"
    path.write_bytes(_part().__cad_interface__(accept=["ocp", "step"])["data"])
    imported = cq.importers.importStep(str(path))
    assert imported.val().Volume() == pytest.approx(EXPECTED_VOLUME, rel=1e-6)


# Consumer


class _Producer:
    """A stand-in for a library with native __cad_interface__ support."""

    def __init__(self, result: dict[str, Any], formats: tuple[str, ...] = ("step",)):
        self.result = result
        self.formats = formats
        self.asked: list[str] | None = None

    def __cad_interface__(self, *, accept: list[str] | None = None) -> dict[str, Any]:
        self.asked = accept
        if accept is not None and not set(accept) & set(self.formats):
            raise ValueError("no common format")
        return self.result


def _step(shape: sf.Shape) -> dict[str, Any]:
    return dict(shape.__cad_interface__(accept=["step"]))


def _translation(x: float, y: float, z: float) -> list[list[float]]:
    return [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]


def test_reads_a_solidfunc_shape() -> None:
    assert sf.volume(sf.import_shape(_part())) == pytest.approx(EXPECTED_VOLUME)


def test_asks_for_step_only() -> None:
    producer = _Producer(_step(_part()))
    sf.import_shape(producer)
    assert producer.asked == ["step"]


def test_assembly_places_shared_geometry_at_world_locations() -> None:
    quarter_turn = [[0, -1, 0, 20], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    assembly = {
        "version": 1,
        "type": "assembly",
        "shapes": [_step(sf.box(size_x=10, size_y=2, size_z=2))],
        "root": {
            "name": "frame",
            "location": _translation(100, 0, 0),
            "color": None,
            "shape": None,
            "children": [
                {
                    "name": "a",
                    "location": _translation(0, 0, 0),
                    "color": None,
                    "shape": 0,
                    "children": [],
                },
                {
                    "name": "b",
                    "location": quarter_turn,
                    "color": (1.0, 0.0, 0.0, 1.0),
                    "shape": 0,
                    "children": [],
                },
            ],
        },
    }
    merged = sf.import_shape(_Producer(assembly))
    assert sf.volume(merged) == pytest.approx(2 * 40)
    lower, upper = sf.bounds(merged)
    # a spans x 95..105; b is turned to run along Y and sits at x 119..121.
    assert lower == pytest.approx((95, -5, 0))
    assert upper == pytest.approx((121, 5, 2))


def test_a_producer_without_step_is_refused() -> None:
    with pytest.raises(ValueError, match="can.t provide STEP"):
        sf.import_shape(_Producer(_step(_part()), formats=("ocp",)))


def test_rejects_an_unknown_version() -> None:
    with pytest.raises(ValueError, match="version 2"):
        sf.import_shape(_Producer({**_step(_part()), "version": 2}))


def test_rejects_a_format_it_did_not_ask_for() -> None:
    with pytest.raises(ValueError, match="returned 'ocp'"):
        sf.import_shape(_Producer({**_step(_part()), "format": "ocp"}))


def test_objects_without_the_protocol() -> None:
    with pytest.raises(TypeError, match="doesn.t support"):
        sf.import_shape(object())


def test_reads_a_cadquery_part(tmp_path: Path) -> None:
    cq = pytest.importorskip("cadquery")
    part = cq.Workplane().box(10, 10, 10).faces(">Z").hole(4)
    path = tmp_path / "cq.step"
    cq.exporters.export(part, str(path))
    # What CadQuery would return with native support, in STEP (AP214).
    producer = _Producer(
        {"version": 1, "type": "shape", "format": "step", "data": path.read_bytes()}
    )
    assert sf.volume(sf.import_shape(producer)) == pytest.approx(
        part.val().Volume(), rel=1e-6
    )
