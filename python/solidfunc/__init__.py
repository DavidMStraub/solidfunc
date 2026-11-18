"""An experimental functional Python API for SolidCore.

Lengths are in millimetres; volumes are in cubic millimetres. Geometry is
opaque and operations leave their inputs unchanged.
"""

from importlib.metadata import version

from ._api import (
    Bounds,
    Point3D,
    bounds,
    box,
    cylinder,
    difference,
    export_step,
    intersection,
    translate,
    union,
    volume,
)
from ._core import KernelError, Shape

__version__ = version("solidfunc")

__all__ = [
    "Bounds",
    "KernelError",
    "Point3D",
    "Shape",
    "__version__",
    "bounds",
    "box",
    "cylinder",
    "difference",
    "export_step",
    "intersection",
    "translate",
    "union",
    "volume",
]
