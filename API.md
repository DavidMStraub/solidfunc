# solidfunc API reference

Import the package as `import solidfunc as sf`. Modeling and mesh functions are
available at the package root. The planar functions are also available from
`solidfunc.planar`.

Lengths and coordinates are in millimetres, volumes are in cubic millimetres,
and angles are in degrees. Geometry operations preserve their inputs.

## Types

| Type | Meaning |
| --- | --- |
| `Point2D` | `tuple[float, float]`, in XY order |
| `Point3D` | `tuple[float, float, float]`, in XYZ order |
| `Bounds` | `tuple[Point3D, Point3D]`, minimum and maximum corners |
| `Curve2D` | Directed XY curve with read-only `start: Point2D` and `end: Point2D` |
| `Path2D` | Connected XY curves with read-only `curves: tuple[Curve2D, ...]` and `is_closed: bool` |
| `Path3D` | Spatial polyline or interpolating spline. Read-only `is_closed`, plus `point_at(parameter: float) -> Point3D` and `tangent_at(parameter: float) -> Point3D`. |
| `Plane` | Right-handed frame with world `origin`, unit `x_dir` and `y_dir`, and a unit `normal`. |
| `Face` | Shape-scoped reference with area centroid `center` and outward unit `normal` (`None` for a nonplanar face). |
| `Edge` | Shape-scoped reference with `kind`, `length`, and optional `circle_center` and `circle_radius`. |
| `Vertex` | Read-only vertex with world XYZ coordinates in `point`. |
| `Mesh` | Indexed display triangles, vertex normals, and visible CAD edge polylines. |
| `Profile` | Opaque filled XY region, optionally with holes |
| `Shape` | Opaque solid geometry that can contain disconnected regions |

## Frames and spatial paths

| Signature | Behavior |
| --- | --- |
| `Plane(*, origin: Point3D = (0.0, 0.0, 0.0), x_dir: Point3D = (1.0, 0.0, 0.0), y_dir: Point3D = (0.0, 1.0, 0.0))` | Keeps the supplied X direction and makes Y perpendicular to it. The default frame is world XY. |
| `Plane.from_normal(*, normal: Point3D, origin: Point3D = (0.0, 0.0, 0.0), x_dir: Point3D \| None = None) -> Plane` | Points local Z along `normal` and projects the optional X direction onto the plane. |
| `Plane.point(x: float, y: float, z: float = 0.0) -> Point3D` | Converts local frame coordinates to world coordinates. |
| `polyline3d(points: Iterable[Point3D], /) -> Path3D` | Joins two or more world points with straight segments. |
| `spline(points: Iterable[Point3D], /, *, degree: int = 3) -> Path3D` | Interpolates a clamped B-spline through world points in traversal order. |

Path evaluation uses a dimensionless parameter on [0, 1]. Each polyline
segment covers an equal share of the interval. Splines use their normalized
knot parameter.

## Curves, paths, and profiles

| Signature | Behavior |
| --- | --- |
| `line(start: Point2D, end: Point2D, /) -> Curve2D` | Directed segment between distinct endpoints. |
| `arc(*, center: Point2D, radius: float, start_angle_deg: float, sweep_angle_deg: float) -> Curve2D` | Circular arc. Start is measured counterclockwise from +X. Sweep is positive counterclockwise or negative clockwise, up to one full turn. |
| `circle(*, radius: float, center: Point2D = (0.0, 0.0)) -> Curve2D` | Full circle starting at its +X point and going counterclockwise. |
| `path(curves: Iterable[Curve2D], /) -> Path2D` | Joins a nonempty sequence in traversal order. Neighboring endpoints must be within 1e-7 mm. The same tolerance determines closure. |
| `profile(outer: Path2D, /, *, holes: Iterable[Path2D] = ()) -> Profile` | Fills a simple closed path. Hole paths must be closed, strictly inside the outer path, and mutually disjoint. Either winding is accepted. |
| `polygon(points: Iterable[Point2D], /) -> Profile` | Fills a simple straight-edged outline from at least three vertices in boundary order. Closure is automatic. |
| `rectangle(*, size_x: float, size_y: float, origin: Point2D = (0.0, 0.0)) -> Profile` | Fills an axis-aligned XY rectangle from its minimum corner. |
| `extrude(profile: Profile, *, distance: float, plane: Plane = Plane()) -> Shape` | Extrudes by a finite, nonzero signed distance normal to the placement plane. Defaults to world XY. |
| `revolve(profile: Profile, *, axis_direction: Point3D, axis_origin: Point3D = (0.0, 0.0, 0.0), angle_deg: float = 360.0, plane: Plane = Plane()) -> Shape` | Revolves a single-boundary profile around an axis in its placement plane. Angle is greater than zero and at most 360 degrees. |
| `loft(sections: Iterable[tuple[Profile, Plane]] \| Iterable[Path3D], /, *, interpolation_deg: int = 1) -> Shape` | Caps a solid through placed profiles or through closed spatial paths with corresponding curves. Sections must be planar and without holes. `interpolation_deg` is a polynomial degree. |
| `sweep(profile: Profile, path: Path3D, /, *, plane: Plane) -> Shape` | Sweeps a profile, including any holes, from the start of the path. Sharp polyline corners are mitred. |

## Solids

| Signature | Behavior |
| --- | --- |
| `box(*, size_x: float, size_y: float, size_z: float, origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Box with positive sizes along +X, +Y, and +Z from its minimum corner. |
| `cylinder(*, radius: float, height: float, origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Cylinder with positive radius and height extending along +Z from its base center. |
| `translate(shape: Shape, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Shape` | Moves a copy by signed offsets along the world axes. |
| `rotate(shape: Shape, *, axis_direction: Point3D, angle_deg: float, axis_origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Rotates a copy about the line through `axis_origin` in the nonzero direction `axis_direction`. Positive angles follow the right-hand rule. |
| `mirror(shape: Shape, *, normal: Point3D, origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Reflects a copy across the plane through `origin` with the specified normal. |
| `union(left: Shape, right: Shape, /) -> Shape` | Material in either operand. Also `left + right`. |
| `intersection(left: Shape, right: Shape, /) -> Shape \| None` | Material in both operands. Returns `None` if empty. |
| `difference(left: Shape, right: Shape, /) -> Shape \| None` | Material in `left` after removing `right`. Also `left - right`. Returns `None` if empty. |

## Topology and finishing

| Signature | Behavior |
| --- | --- |
| `faces(scope: Shape \| Edge, /) -> tuple[Face, ...]` | Returns read-only faces of a shape or unique faces incident to an edge. |
| `edges(scope: Shape \| Face, /) -> tuple[Edge, ...]` | Returns read-only edges of a shape or the unique boundary edges of a face, including hole rims. |
| `vertices(scope: Shape \| Face \| Edge, /) -> tuple[Vertex, ...]` | Returns unique topological vertices, including vertices on face holes. |
| `face_plane(face: Face, /, *, x_dir: Point3D \| None = None) -> Plane` | Places a frame at a planar face's centroid with its normal pointing outward. |
| `fillet(shape: Shape, edges: Iterable[Edge], /, *, radius: float) -> Shape` | Rounds selected edges on a copy. The references must come from this exact shape. |
| `chamfer(shape: Shape, edges: Iterable[Edge], /, *, setback: float) -> Shape` | Bevels selected edges on a copy with equal setbacks along the adjacent faces. The references must come from this exact shape. |

## Measurement and STEP exchange

| Signature | Behavior |
| --- | --- |
| `bounds(shape: Shape) -> Bounds` | Returns the world-axis-aligned bounding box. |
| `volume(shape: Shape, *, relative_tolerance: float = 1e-9) -> float` | Returns enclosed volume. The requested relative integration tolerance is positive and dimensionless. |
| `import_step(path: str \| PathLike[str], /) -> Shape` | Reads closed STEP solids, places their occurrences in world coordinates, and unites them as a single shape. |
| `export_step(shape: Shape, path: str \| PathLike[str], *, name: str = "Part") -> None` | Writes STEP AP242, using `name` as the part label. Overwrites an existing file. |

Invalid argument values can raise `ValueError`. Kernel failures raise
`KernelError` (a `RuntimeError` subclass). Filesystem errors from STEP exchange
propagate as `OSError` subclasses.


## Visualization

| Signature | Behavior |
| --- | --- |
| `tessellate(shape: Shape, /, *, chord_tolerance: float \| None = None) -> Mesh` | Uses SolidCore to approximate a shape with triangles and CAD outlines. Chord tolerance is a positive target deviation in millimetres and defaults to a value based on the shape's size. |
| `solidfunc.view.show(shape: Shape, /, *, chord_tolerance: float \| None = None, screenshot: str \| PathLike[str] \| None = None, jupyter_backend: str = "static") -> None` | Uses optional PyVista to display a part or save a PNG. In Jupyter the default is static. Install `pyvista[jupyter]` for the interactive `"client"` backend. |
