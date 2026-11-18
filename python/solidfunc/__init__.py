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
from ._core import Solid, SolidCoreError

__version__ = version("solidfunc")

__all__ = [
    "Bounds",
    "Point3D",
    "Solid",
    "SolidCoreError",
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
