"""Rigid frames for placing XY geometry and shapes in model space."""

from dataclasses import dataclass, replace
from math import hypot, isfinite

from . import _core
from ._api import Point3D
from ._core import Face, Shape


def _vector(value: Point3D) -> Point3D:
    x, y, z = value
    if not all(map(isfinite, (x, y, z))):
        raise ValueError("plane coordinates and directions must be finite")
    return x, y, z


def _unit(value: Point3D) -> Point3D:
    x, y, z = value
    scale = max(abs(x), abs(y), abs(z))
    if scale == 0:
        raise ValueError("plane directions must be nonzero and independent")
    x, y, z = x / scale, y / scale, z / scale
    length = hypot(x, y, z)
    return x / length, y / length, z / length


def _cross(a: Point3D, b: Point3D) -> Point3D:
    ax, ay, az = a
    bx, by, bz = b
    return ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx


@dataclass(frozen=True, slots=True, kw_only=True)
class Plane:
    """Right-handed coordinate frame for a profile.

    Supply ``origin`` in world millimetres. ``x_dir`` fixes the positive
    local X direction. ``y_dir`` determines the positive side of local Y
    and is made perpendicular to X. Directions must be finite, nonzero,
    and nonparallel. The default frame is world XY.
    """

    origin: Point3D = (0.0, 0.0, 0.0)
    x_dir: Point3D = (1.0, 0.0, 0.0)
    y_dir: Point3D = (0.0, 1.0, 0.0)

    def __post_init__(self) -> None:
        x = _unit(_vector(self.x_dir))
        cross = _cross(x, _unit(_vector(self.y_dir)))
        if hypot(*cross) <= 1e-12:
            raise ValueError("plane directions must be nonparallel")
        normal = _unit(cross)
        object.__setattr__(self, "origin", _vector(self.origin))
        object.__setattr__(self, "x_dir", x)
        object.__setattr__(self, "y_dir", _unit(_cross(normal, x)))

    @classmethod
    def from_normal(
        cls,
        *,
        normal: Point3D,
        origin: Point3D = (0.0, 0.0, 0.0),
        x_dir: Point3D | None = None,
    ) -> "Plane":
        """Place a frame with its local Z along the given world direction.

        ``normal`` must be finite and nonzero. ``origin`` is in world
        millimetres. ``x_dir`` is projected onto the plane to set positive
        local X. It must be finite, nonzero, and nonparallel to the normal.
        If omitted, use the world axis least aligned with the normal.
        """
        normal = _unit(_vector(normal))
        if x_dir is None:
            axes: tuple[Point3D, ...] = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
            directions = zip(normal, axes, strict=True)
            x_dir = min(directions, key=lambda pair: abs(pair[0]))[1]
        y_dir = _cross(normal, _unit(_vector(x_dir)))
        if hypot(*y_dir) <= 1e-12:
            raise ValueError("plane x direction must be nonparallel to the normal")
        return cls(origin=origin, x_dir=_cross(y_dir, normal), y_dir=y_dir)

    @classmethod
    def from_face(cls, face: Face, /, *, x_dir: Point3D | None = None) -> "Plane":
        """Place a frame at a planar face's centroid, with its normal outward.

        ``x_dir`` is a world direction projected onto the face to orient local
        X. If omitted, use the world axis least aligned with the normal.
        A nonplanar face or a direction parallel to the normal raises
        ``ValueError``.
        """
        normal = face.planar_normal
        if normal is None:
            raise ValueError("Plane.from_face requires a planar face")
        return cls.from_normal(origin=face.centroid, normal=normal, x_dir=x_dir)

    @property
    def normal(self) -> Point3D:
        """Return the unit world direction of positive local Z."""
        return _unit(_cross(self.x_dir, self.y_dir))

    def offset(self, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> "Plane":
        """Return this frame moved by local offsets, keeping its orientation.

        ``x``, ``y``, and ``z`` are signed millimetres along this frame's own
        X, Y, and normal directions.
        """
        return replace(self, origin=self.point(x, y, z))

    def point(self, x: float, y: float, z: float = 0.0) -> Point3D:
        """Map local XYZ coordinates in millimetres to world XYZ."""

        ox, oy, oz = self.origin
        xx, xy, xz = self.x_dir
        yx, yy, yz = self.y_dir
        zx, zy, zz = self.normal
        return (
            ox + x * xx + y * yx + z * zx,
            oy + x * xy + y * yy + z * zy,
            oz + x * xz + y * yz + z * zz,
        )


def place(shape: Shape, plane: Plane, /) -> Shape:
    """Return a copy of ``shape`` carried from world XY onto ``plane``.

    The world origin moves to ``plane.origin`` and the world X, Y, and Z
    axes turn onto the plane's X direction, Y direction, and normal. A
    primitive built at the origin therefore lands centred on the plane with
    its base on it, for example ``place(stud, Plane.from_face(top))``.
    """
    return _core._place(shape, plane.origin, plane.x_dir, plane.y_dir, plane.normal)


_XY = Plane()
