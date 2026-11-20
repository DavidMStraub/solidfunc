"""Check the inline notebook representations of shapes."""

import json
import re
import xml.etree.ElementTree as ET

import solidfunc as sf
from solidfunc._display import VTK_JS_URL


def plate() -> sf.Shape:
    return sf.box(size_x=80, size_y=50, size_z=10) - sf.cylinder(diameter=20, height=10)


def test_mimebundle_offers_text_svg_and_html() -> None:
    bundle = plate()._repr_mimebundle_()
    assert set(bundle) == {"text/plain", "image/svg+xml", "text/html"}
    assert bundle["text/plain"] == repr(plate())


def test_svg_is_well_formed_and_draws_faces_and_edges() -> None:
    svg = plate()._repr_mimebundle_()["image/svg+xml"]
    root = ET.fromstring(svg)
    namespace = "{http://www.w3.org/2000/svg}"
    assert root.findall(f".//{namespace}polygon")
    assert root.findall(f".//{namespace}line")


def test_svg_culls_back_faces() -> None:
    box = sf.box(size_x=1, size_y=1, size_z=1)
    svg = box._repr_mimebundle_(include={"image/svg+xml"})["image/svg+xml"]
    # The isometric view sees three of the six faces, two triangles each.
    assert svg.count("<polygon") == 6


def test_html_embeds_svg_fallback_and_mesh_for_pinned_vtk_js() -> None:
    html = plate()._repr_mimebundle_(include={"text/html"})["text/html"]
    assert "<svg" in html
    assert json.dumps(VTK_JS_URL) in html
    assert re.fullmatch(
        r"https://cdn\.jsdelivr\.net/npm/vtk\.js@\d+\.\d+\.\d+/vtk\.js", VTK_JS_URL
    )
    data = json.loads(re.search(r", (\{.*\})\);</script>$", html)[1])  # type: ignore[index]
    assert len(data["points"]) == len(data["normals"])
    assert len(data["polys"]) % 4 == 0
    assert data["lines"]


def test_include_and_exclude_filter_representations() -> None:
    shape = plate()
    assert set(shape._repr_mimebundle_(include={"text/plain"})) == {"text/plain"}
    assert set(shape._repr_mimebundle_(exclude={"text/html"})) == {
        "text/plain",
        "image/svg+xml",
    }
