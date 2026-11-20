"""The geometry kinds that topology references report.

Kinds are plain strings at runtime. The Literal types let a type checker
reject a misspelled comparison such as ``face.kind == "cylindre"``.
"""

from typing import Literal, TypeAlias

EdgeKind: TypeAlias = Literal[
    "line", "circle", "ellipse", "polyline", "spline", "intersection"
]
"""How an edge's curve is stored."""

FaceKind: TypeAlias = Literal[
    "plane",
    "cylinder",
    "cone",
    "sphere",
    "torus",
    "spline",
    "revolution",
    "blend",
]
"""How a face's surface is stored."""
