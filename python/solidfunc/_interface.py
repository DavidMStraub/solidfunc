"""The ``__cad_interface__`` protocol in the ``"step"`` format.

See https://github.com/DavidMStraub/cad-interface. A consumer calls
``obj.__cad_interface__(accept=[...])`` with the formats it reads, most
preferred first. SolidCore is not OpenCASCADE, so solidfunc can neither
offer nor read the in-memory ``"ocp"`` shape or OCCT's BREP formats, only
STEP.

- As a producer, ``Shape.__cad_interface__`` returns the shape as STEP.
- As a consumer, ``import_shape`` reads any object that offers STEP.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from . import _core
from ._core import Shape

FORMAT: Literal["step"] = "step"


class ShapeDict(TypedDict):
    """A single shape, as version 1 of the protocol defines it."""

    version: Literal[1]
    type: Literal["shape"]
    format: Literal["step"]
    data: bytes


def _cad_interface(shape: Shape, accept: Sequence[str] | None) -> ShapeDict:
    """Return ``shape`` as STEP bytes if the consumer accepts STEP."""
    if isinstance(accept, str):
        raise TypeError('accept must be a sequence of format names, e.g. ["step"]')
    if accept is not None and FORMAT not in accept:
        raise ValueError(
            f"solidfunc offers only the {FORMAT!r} format; the consumer accepts "
            f"{list(accept)!r}"
        )
    text = _core._step_text(shape, "", "Part")
    return {
        "version": 1,
        "type": "shape",
        "format": FORMAT,
        "data": text.encode("utf-8"),
    }


def import_shape(obj: object, /) -> Shape:
    """Import a part or assembly from another CAD library as a solidfunc shape.

    ``obj`` is, for example, a CadQuery or build123d part. This works with
    any library that supports the ``__cad_interface__`` protocol and can
    provide STEP. An assembly becomes one shape with every part at its
    place; names and colours are not kept. Each call converts the part, so
    import it once and reuse the result.
    """
    method = getattr(obj, "__cad_interface__", None)
    if method is None:
        raise TypeError(
            f"solidfunc can't import a {type(obj).__name__}: its library doesn't "
            "support the __cad_interface__ protocol"
        )
    try:
        result = method(accept=[FORMAT])
    except ValueError as error:
        raise ValueError(
            f"solidfunc can't import a {type(obj).__name__}: its library can't "
            "provide STEP, the only format solidfunc reads"
        ) from error
    if result.get("version") != 1:
        raise ValueError(
            f"unsupported __cad_interface__ version {result.get('version')!r}"
        )
    kind = result.get("type")
    if kind == "shape":
        return _read_shape(result)
    if kind == "assembly":
        return _read_assembly(result)
    raise ValueError(f"unknown __cad_interface__ type {kind!r}")


def _read_shape(shape: Mapping[str, Any]) -> Shape:
    if shape.get("format") != FORMAT:
        raise ValueError(
            f"asked for {FORMAT!r} but the producer returned {shape.get('format')!r}"
        )
    data = shape["data"]
    # STEP files are ISO 8859-1; import_step decodes the same way.
    return _core._import_step(bytes(data).decode("latin-1"))


_IDENTITY = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def _product(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[i][k] * right[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def _read_assembly(assembly: Mapping[str, Any]) -> Shape:
    geometry = [_read_shape(entry) for entry in assembly["shapes"]]
    placed: list[Shape] = []

    def visit(node: Mapping[str, Any], parent: list[list[float]]) -> None:
        location = _product(parent, [list(map(float, row)) for row in node["location"]])
        if node.get("shape") is not None:
            placed.append(_placed(geometry[node["shape"]], location))
        for child in node.get("children", ()):
            visit(child, location)

    visit(assembly["root"], _IDENTITY)
    if not placed:
        raise ValueError("the assembly has no geometry")
    if len(placed) == 1:
        return placed[0]
    return _core._union_all(placed)


def _placed(shape: Shape, matrix: list[list[float]]) -> Shape:
    """A copy of ``shape`` moved by a rigid 4×4 transform (column vectors)."""
    origin = (matrix[0][3], matrix[1][3], matrix[2][3])
    x, y, z = ((matrix[0][c], matrix[1][c], matrix[2][c]) for c in range(3))
    return _core._place(shape, origin, x, y, z)
