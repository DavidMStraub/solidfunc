"""Optional PyVista display for solidfunc shapes."""

from importlib import import_module
from os import PathLike

from ._api import Point3D
from ._core import Shape
from ._mesh import tessellate

__all__ = ["show"]


def show(
    shape: Shape,
    /,
    *,
    chord_tolerance: float | None = None,
    screenshot: str | PathLike[str] | None = None,
    jupyter_backend: str = "static",
) -> None:
    """Display a shaded part and its CAD edges with PyVista.

    Install PyVista separately. ``chord_tolerance`` is the target
    tessellation deviation in millimetres. With ``screenshot``, save
    a PNG to that path using off-screen rendering. Otherwise PyVista
    opens a desktop viewer or displays the part in the notebook.
    ``jupyter_backend`` defaults to a static image. Set it to
    ``"client"`` with ``pyvista[jupyter]`` installed for interaction.
    """
    try:
        pv = import_module("pyvista")
    except ModuleNotFoundError as exc:
        if exc.name != "pyvista":
            raise
        raise ImportError(
            "solidfunc.view.show requires PyVista. Install pyvista."
        ) from exc

    np = import_module("numpy")
    mesh = tessellate(shape, chord_tolerance=chord_tolerance)
    surface = pv.PolyData(
        np.asarray(mesh.vertices),
        faces=np.asarray([(3, *tri) for tri in mesh.triangles]),
    )
    surface.point_data.active_normals = np.asarray(mesh.normals)

    plotter = pv.Plotter(
        off_screen=screenshot is not None,
        notebook=False if screenshot is not None else None,
        window_size=(900, 620),
    )
    try:
        plotter.set_background("#f4f6fa")
        # Shade with the kernel's vertex normals; flat shading shows every facet.
        plotter.add_mesh(surface, color="#6fa0bc", specular=0.16, smooth_shading=True)
        if mesh.edge_polylines:
            points: list[Point3D] = []
            lines: list[int] = []
            for polyline in mesh.edge_polylines:
                start = len(points)
                points.extend(polyline)
                lines.extend((len(polyline), *range(start, len(points))))
            outline = pv.PolyData(np.asarray(points), lines=np.asarray(lines))
            plotter.add_mesh(outline, color="#263e52", line_width=1.4)
        plotter.view_isometric()
        if screenshot is not None:
            plotter.show(screenshot=str(screenshot), interactive=False)
        elif plotter.notebook:
            plotter.show(jupyter_backend=jupyter_backend)
        else:
            plotter.show()
    except BaseException:
        plotter.close()
        raise
    else:
        if plotter.notebook and jupyter_backend == "static":
            plotter.close()
