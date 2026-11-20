"""Inline notebook display for shapes, without Python dependencies.

Notebook frontends call ``Shape._repr_mimebundle_``, which returns three
representations of the same tessellation:

- ``text/plain``: the shape's ``repr``.
- ``image/svg+xml``: a static isometric view drawn in Python, for frontends
  that don't run scripts (GitHub, nbviewer, untrusted notebooks).
- ``text/html``: the same SVG as a fallback, replaced by an interactive
  vtk.js view once the script has loaded vtk.js from a CDN.
"""

import itertools
import json
import math
from collections.abc import Container, Sequence
from uuid import uuid4

from ._api import Point3D
from ._core import Shape
from ._mesh import Mesh, tessellate

__all__ = ["mimebundle"]

# Pinned: the HTML loads this script into the user's notebook.
VTK_JS_URL = "https://cdn.jsdelivr.net/npm/vtk.js@38.0.5/vtk.js"

FACE_RGB = (111, 160, 188)  # "#6fa0bc", as in view.show
EDGE_COLOR = "#263e52"
BACKGROUND = "#f4f6fa"
SVG_SIZE = 360.0
SVG_MARGIN = 12.0
HTML_HEIGHT_PX = 400


def mimebundle(
    shape: Shape,
    include: Container[str] | None = None,
    exclude: Container[str] | None = None,
) -> dict[str, str]:
    """Return the representations a notebook frontend asks for."""

    def wanted(mime: str) -> bool:
        return (include is None or mime in include) and (
            exclude is None or mime not in exclude
        )

    bundle: dict[str, str] = {}
    if wanted("text/plain"):
        bundle["text/plain"] = repr(shape)
    if wanted("image/svg+xml") or wanted("text/html"):
        mesh = tessellate(shape)
        svg = _svg(mesh)
        if wanted("image/svg+xml"):
            bundle["image/svg+xml"] = svg
        if wanted("text/html"):
            bundle["text/html"] = _html(mesh, svg)
    return bundle


# --- Static SVG -------------------------------------------------------------


def _sub(a: Sequence[float], b: Sequence[float]) -> Point3D:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Sequence[float], b: Sequence[float]) -> Point3D:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(a: Sequence[float]) -> Point3D:
    length = math.sqrt(_dot(a, a))
    return (a[0] / length, a[1] / length, a[2] / length)


# Isometric camera looking from (+x, +y, +z) towards the part, Z up.
_TOWARD_VIEWER = _unit((1.0, 1.0, 1.0))
_RIGHT = _unit(_cross((0.0, 0.0, 1.0), _TOWARD_VIEWER))
_UP = _cross(_TOWARD_VIEWER, _RIGHT)
_LIGHT = _unit(
    tuple(
        v + 0.5 * u - 0.1 * r
        for v, u, r in zip(_TOWARD_VIEWER, _UP, _RIGHT, strict=True)
    )
)


def _svg(mesh: Mesh) -> str:
    """Draw visible triangles and edges back to front (painter's algorithm)."""
    if not mesh.vertices:
        return _svg_document("", 1, 1)
    projected = [(_dot(p, _RIGHT), -_dot(p, _UP)) for p in mesh.vertices]
    depth = [_dot(p, _TOWARD_VIEWER) for p in mesh.vertices]

    xs = [x for x, _ in projected]
    ys = [y for _, y in projected]
    min_x, min_y = min(xs), min(ys)
    extent = max(max(xs) - min_x, max(ys) - min_y) or 1.0
    scale = (SVG_SIZE - 2 * SVG_MARGIN) / extent
    width = (max(xs) - min_x) * scale + 2 * SVG_MARGIN
    height = (max(ys) - min_y) * scale + 2 * SVG_MARGIN

    def screen(p: Point3D) -> tuple[str, str]:
        x = (_dot(p, _RIGHT) - min_x) * scale + SVG_MARGIN
        y = (-_dot(p, _UP) - min_y) * scale + SVG_MARGIN
        return f"{x:.1f}", f"{y:.1f}"

    front = [
        (a, b, c)
        for a, b, c in mesh.triangles
        if _dot(
            _cross(
                _sub(mesh.vertices[b], mesh.vertices[a]),
                _sub(mesh.vertices[c], mesh.vertices[a]),
            ),
            _TOWARD_VIEWER,
        )
        > 0
    ]
    items: list[tuple[float, str]] = []
    for a, b, c in front:
        pa, pb, pc = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        na, nb, nc = mesh.normals[a], mesh.normals[b], mesh.normals[c]
        normal = (na[0] + nb[0] + nc[0], na[1] + nb[1] + nc[1], na[2] + nb[2] + nc[2])
        shade = 0.5 + 0.5 * max(0.0, _dot(_unit(normal), _LIGHT))
        red, green, blue = (min(255, round(channel * shade)) for channel in FACE_RGB)
        color = f"#{red:02x}{green:02x}{blue:02x}"
        points = " ".join(",".join(screen(p)) for p in (pa, pb, pc))
        items.append(
            (
                (depth[a] + depth[b] + depth[c]) / 3,
                f'<polygon points="{points}" fill="{color}" stroke="{color}"/>',
            )
        )

    items.sort(key=lambda item: item[0])
    faces = "".join(element for _, element in items)

    # Edges go on top, but only the pieces no front face covers.
    covers = _Occlusion(projected, depth, front, extent)
    step = extent / 60
    lines: list[str] = []
    for polyline in mesh.edge_polylines:
        for start, end in itertools.pairwise(polyline):
            pieces = max(1, math.ceil(math.dist(start, end) / step))
            for i in range(pieces):
                s = _lerp(start, end, i / pieces)
                e = _lerp(start, end, (i + 1) / pieces)
                if covers(_lerp(s, e, 0.5)):
                    continue
                (x1, y1), (x2, y2) = screen(s), screen(e)
                lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    return _svg_document(faces + "".join(lines), width, height)


def _lerp(a: Point3D, b: Point3D, t: float) -> Point3D:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


class _Occlusion:
    """Test whether a front-facing triangle lies in front of a point.

    Triangles are bucketed on a screen-space grid so each test only looks at
    the few triangles near the point.
    """

    CELLS = 48

    def __init__(
        self,
        projected: list[tuple[float, float]],
        depth: list[float],
        triangles: list[tuple[int, int, int]],
        extent: float,
    ) -> None:
        self.projected = projected
        self.depth = depth
        self.triangles = triangles
        self.min_x = min(x for x, _ in projected)
        self.min_y = min(y for _, y in projected)
        self.cell = extent / self.CELLS
        # Points on a face's own boundary must not count as covered.
        self.tolerance = 1e-3 * extent
        self.grid: dict[tuple[int, int], list[int]] = {}
        for index, triangle in enumerate(triangles):
            xs = [projected[i][0] for i in triangle]
            ys = [projected[i][1] for i in triangle]
            for gx in range(self._cell_x(min(xs)), self._cell_x(max(xs)) + 1):
                for gy in range(self._cell_y(min(ys)), self._cell_y(max(ys)) + 1):
                    self.grid.setdefault((gx, gy), []).append(index)

    def _cell_x(self, x: float) -> int:
        return int((x - self.min_x) / self.cell)

    def _cell_y(self, y: float) -> int:
        return int((y - self.min_y) / self.cell)

    def __call__(self, point: Point3D) -> bool:
        px, py = _dot(point, _RIGHT), -_dot(point, _UP)
        pz = _dot(point, _TOWARD_VIEWER)
        for index in self.grid.get((self._cell_x(px), self._cell_y(py)), ()):
            a, b, c = self.triangles[index]
            (ax, ay), (bx, by), (cx, cy) = (
                self.projected[a],
                self.projected[b],
                self.projected[c],
            )
            area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
            if area == 0:
                continue
            u = ((bx - px) * (cy - py) - (cx - px) * (by - py)) / area
            v = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) / area
            w = 1 - u - v
            if min(u, v, w) < 0:
                continue
            surface = u * self.depth[a] + v * self.depth[b] + w * self.depth[c]
            if surface > pz + self.tolerance:
                return True
        return False


def _svg_document(body: str, width: float, height: float) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" '
        f'style="background:{BACKGROUND};max-width:100%;height:auto">'
        f'<g stroke-width="0.6" stroke-linejoin="round">{body}</g>'
        f"<style>line{{stroke:{EDGE_COLOR};stroke-width:1.2;"
        "stroke-linecap:round}</style></svg>"
    )


# --- Interactive HTML -------------------------------------------------------


def _html(mesh: Mesh, svg: str) -> str:
    element_id = f"solidfunc-{uuid4().hex}"
    lines: list[int] = []
    edge_points: list[float] = []
    for polyline in mesh.edge_polylines:
        start = len(edge_points) // 3
        lines.append(len(polyline))
        lines.extend(range(start, start + len(polyline)))
        edge_points.extend(round(c, 4) for p in polyline for c in p)
    data = {
        "points": [round(c, 4) for p in mesh.vertices for c in p],
        "normals": [round(c, 4) for n in mesh.normals for c in n],
        "polys": [i for t in mesh.triangles for i in (3, *t)],
        "edgePoints": edge_points,
        "lines": lines,
    }
    return (
        f'<div id="{element_id}" style="width:100%;max-width:720px;'
        f'height:{HTML_HEIGHT_PX}px;position:relative;background:{BACKGROUND}">'
        '<div style="display:flex;align-items:center;justify-content:center;'
        f'height:100%">{svg}</div></div>'
        f"<script>({_SCRIPT})({json.dumps(element_id)}, {json.dumps(VTK_JS_URL)}, "
        f"{json.dumps(data, separators=(',', ':'))});</script>"
    )


_SCRIPT = """function (elementId, url, data) {
  function withVtk(callback) {
    if (window.vtk) return callback(window.vtk);
    if (typeof window.require === "function" && window.require.config) {
      window.require.config({paths: {"solidfunc-vtk": url.replace(/\\.js$/, "")}});
      window.require(["solidfunc-vtk"], callback);
      return;
    }
    let script = document.querySelector("script[data-solidfunc-vtk]");
    if (!script) {
      script = document.createElement("script");
      script.src = url;
      script.dataset.solidfuncVtk = "";
      document.head.appendChild(script);
    }
    script.addEventListener("load", () => callback(window.vtk));
  }

  function polyData(vtk, points, cells, kind) {
    const result = vtk.Common.DataModel.vtkPolyData.newInstance();
    result.getPoints().setData(Float32Array.from(points), 3);
    result[kind]().setData(Uint32Array.from(cells));
    return result;
  }

  function actor(vtk, input) {
    const mapper = vtk.Rendering.Core.vtkMapper.newInstance();
    mapper.setInputData(input);
    const result = vtk.Rendering.Core.vtkActor.newInstance();
    result.setMapper(mapper);
    return [result, mapper];
  }

  withVtk(function (vtk) {
    const element = document.getElementById(elementId);
    if (!element || !vtk) return;
    element.innerHTML = "";
    const view = vtk.Rendering.Misc.vtkGenericRenderWindow.newInstance({
      background: [0.957, 0.965, 0.98],
    });
    view.setContainer(element);
    const renderer = view.getRenderer();

    const surface = polyData(vtk, data.points, data.polys, "getPolys");
    surface.getPointData().setNormals(vtk.Common.Core.vtkDataArray.newInstance({
      name: "Normals", numberOfComponents: 3, values: Float32Array.from(data.normals),
    }));
    const [faces, faceMapper] = actor(vtk, surface);
    faceMapper.setResolveCoincidentTopologyToPolygonOffset();
    faceMapper.setResolveCoincidentTopologyPolygonOffsetParameters(1, 1);
    faces.getProperty().setColor(0.435, 0.627, 0.737);
    faces.getProperty().setSpecular(0.1);
    faces.getProperty().setSpecularPower(50);
    renderer.addActor(faces);

    if (data.lines.length) {
      const outline = polyData(vtk, data.edgePoints, data.lines, "getLines");
      const [edges] = actor(vtk, outline);
      edges.getProperty().setColor(0.149, 0.243, 0.322);
      renderer.addActor(edges);
    }

    // A headlight shades the three faces of an isometric box alike; light
    // from the upper left instead, as in the SVG.
    renderer.setAutomaticLightCreation(false);
    const light = vtk.Rendering.Core.vtkLight.newInstance();
    light.setLightTypeToCameraLight();
    light.setPosition(-0.3, 0.6, 1);
    renderer.addLight(light);
    faces.getProperty().setAmbient(0.5);
    faces.getProperty().setDiffuse(0.3);

    const camera = renderer.getActiveCamera();
    camera.setFocalPoint(0, 0, 0);
    camera.setPosition(1, 1, 1);
    camera.setViewUp(0, 0, 1);
    renderer.resetCamera();
    view.resize();
    if (window.ResizeObserver) new ResizeObserver(() => view.resize()).observe(element);
    view.getRenderWindow().render();
  });
}"""
