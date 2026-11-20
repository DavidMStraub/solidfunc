"""An experimental functional Python API for SolidCore.

Lengths are in millimetres; volumes are in cubic millimetres. Geometry is
opaque and operations leave their inputs unchanged.
"""

from importlib.metadata import version

from . import planar
from ._api import (
    Bounds,
    Point3D,
    bounds,
    box,
    cylinder,
    difference,
    export_step,
    import_step,
    intersection,
    mirror,
    rotate,
    translate,
    union,
    volume,
)
from ._core import (
    Edge,
    EmptyResultError,
    Face,
    KernelError,
    Path3D,
    Profile,
    Shape,
    Vertex,
)
from ._frame import Plane, place
from ._kinds import EdgeKind, FaceKind
from ._mesh import Mesh, tessellate
from ._modeling import loft, polyline3d, revolve, spline3d, sweep
from ._topology import chamfer, edges, faces, fillet, vertices
from .planar import (
    Boundary,
    Curve2D,
    Path2D,
    Point2D,
    arc,
    circle,
    extrude,
    line,
    path,
    polygon,
    polyline,
    profile,
    rectangle,
)

__version__ = version("solidfunc")

__all__ = [
    "Boundary",
    "Bounds",
    "Curve2D",
    "Edge",
    "EdgeKind",
    "EmptyResultError",
    "Face",
    "FaceKind",
    "KernelError",
    "Mesh",
    "Path2D",
    "Path3D",
    "Plane",
    "Point2D",
    "Point3D",
    "Profile",
    "Shape",
    "Vertex",
    "__version__",
    "arc",
    "bounds",
    "box",
    "chamfer",
    "circle",
    "cylinder",
    "difference",
    "edges",
    "export_step",
    "extrude",
    "faces",
    "fillet",
    "import_step",
    "intersection",
    "line",
    "loft",
    "mirror",
    "path",
    "place",
    "planar",
    "polygon",
    "polyline",
    "polyline3d",
    "profile",
    "rectangle",
    "revolve",
    "rotate",
    "spline3d",
    "sweep",
    "tessellate",
    "translate",
    "union",
    "vertices",
    "volume",
]
