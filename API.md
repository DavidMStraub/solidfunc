# solidfunc API reference

Import the package as `import solidfunc as sf`. Modeling and mesh functions are
available at the package root. The planar functions are also available from
`solidfunc.planar`.

Lengths and coordinates are in millimetres, volumes are in cubic millimetres,
and angles are in degrees. Geometry operations preserve their inputs.

Naming conventions: planar constructors have no suffix (`line`, `polyline`,
`circle`), and spatial constructors that take world XYZ points end in `3d`
(`polyline3d`, `spline3d`). A `_deg` suffix always names an angle in degrees;
a polynomial degree is spelled `degree`.

`Point2D` and `Point3D` are coordinate tuple aliases. `Bounds` is a named
tuple `(min, max)` of XYZ corners with `.size` and `.center` properties. Instantiate `Plane` directly or use one of its factories. `Mesh`
is a dataclass that can also be constructed directly. The native geometry
and topology types are created by the functions listed below.

## Placement frames

| Signature | Behavior |
| --- | --- |
| `Plane(*, origin: Point3D = (0.0, 0.0, 0.0), x_dir: Point3D = (1.0, 0.0, 0.0), y_dir: Point3D = (0.0, 1.0, 0.0))` | Keeps the supplied X direction and makes Y perpendicular to it. The default frame is world XY. |
| `Plane.from_normal(*, normal: Point3D, origin: Point3D = (0.0, 0.0, 0.0), x_dir: Point3D \| None = None) -> Plane` | Points local Z along `normal` and projects the optional X direction onto the plane. |
| `Plane.from_face(face: Face, /, *, x_dir: Point3D \| None = None) -> Plane` | Uses a planar face's centroid and outward normal. Projects the optional X direction onto the plane. |
| `Plane.point(x: float, y: float, z: float = 0.0) -> Point3D` | Converts local frame coordinates to world coordinates. |
| `Plane.offset(*, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Plane` | Moves the frame by offsets along its own X, Y, and normal directions, keeping its orientation. |
| `place(shape: Shape, plane: Plane, /) -> Shape` | Carries a copy from world XY onto the plane: the origin to `plane.origin`, world X, Y, and Z onto the plane's X, Y, and normal. A primitive lands centred on the plane with its base on it. |

## Planar construction

Curves and paths are boundaries; a `Profile` is a filled region. Only a
`Profile` becomes a solid: `extrude`, `revolve`, `sweep`, and `loft` raise
`TypeError` for a curve or path. `Curve2D` stores a native analytic line or
arc. `Path2D` stores an ordered chain of these curves, exposed by `.curves`,
and reports closure via `.is_closed`. `Boundary` is the alias
`Curve2D | Path2D`.

| Signature | Behavior |
| --- | --- |
| `line(start: Point2D, end: Point2D, /) -> Curve2D` | Directed segment between distinct endpoints. |
| `arc(*, center: Point2D, radius: float, start_angle_deg: float, sweep_angle_deg: float) -> Curve2D` | Circular arc. Start is measured counterclockwise from +X. Sweep is positive counterclockwise or negative clockwise, up to one full turn. |
| `circle(*, radius: float \| diameter: float, center: Point2D = (0.0, 0.0)) -> Curve2D` | Full circle starting at its +X point and going counterclockwise. Give exactly one of `radius` or `diameter`. |
| `path(curves: Iterable[Curve2D], /) -> Path2D` | Joins a nonempty sequence in traversal order. Neighboring endpoints must be within 1e-7 mm. The same tolerance determines closure. |
| `polyline(points: Iterable[Point2D], /) -> Path2D` | Straight segments through at least two points. Open unless the last point repeats the first. |
| `polygon(points: Iterable[Point2D], /) -> Path2D` | Closed straight-edged boundary through at least three vertices in boundary order. Closure is automatic. |
| `rectangle(*, size_x: float, size_y: float, center: Point2D = (0.0, 0.0)) -> Path2D` | Closed axis-aligned rectangle boundary around `center`. |
| `profile(outer: Boundary, /, *, holes: Iterable[Boundary] = ()) -> Profile` | Fills a simple closed boundary. A single closed curve such as a circle is accepted directly. Holes must be closed, strictly inside the outer boundary, and mutually disjoint. Either winding is accepted. |

## Spatial paths

`Path3D` stores native line segments or an interpolating B-spline with its
control points and knots. It exposes `.is_closed`, `.point_at(parameter)`,
and `.tangent_at(parameter)`.

| Signature | Behavior |
| --- | --- |
| `polyline3d(points: Iterable[Point3D], /) -> Path3D` | Joins two or more world points with straight segments. |
| `spline3d(points: Iterable[Point3D], /, *, degree: int = 3) -> Path3D` | Interpolates a clamped B-spline through world points in traversal order. |

Path evaluation uses a dimensionless parameter on [0, 1]. Each polyline
segment covers an equal share of the interval. Splines use their normalized
knot parameter.

## Building solids

`Shape` holds a native solid B-rep, which can contain disconnected regions.

| Signature | Behavior |
| --- | --- |
| `box(*, size_x: float, size_y: float, size_z: float) -> Shape` | Box with positive sizes, centred in X and Y, rising from z = 0 to `size_z`. |
| `cylinder(*, radius: float \| diameter: float, height: float) -> Shape` | Cylinder on the Z axis, rising from z = 0 to `height`. Give exactly one of `radius` or `diameter`. |
| `sphere(*, radius: float \| diameter: float) -> Shape` | Sphere on the Z axis resting on z = 0, so its centre is at z = `radius`. Give exactly one of `radius` or `diameter`. |
| `cone(*, base_radius: float \| base_diameter: float, top_radius: float \| top_diameter: float, height: float) -> Shape` | Cone or frustum on the Z axis, rising from z = 0 to `height`. The base is positive; the top is zero for a pointed cone, may be larger than the base, and may not equal it. Give one of radius or diameter for each end. |
| `torus(*, major_radius: float, minor_radius: float) -> Shape` | Ring torus around the Z axis resting on z = 0. `major_radius` reaches the centre of the tube and is larger than the tube's `minor_radius`. |
| `extrude(profile: Profile, *, distance: float, plane: Plane = Plane()) -> Shape` | Extrudes by a finite, nonzero signed distance normal to the placement plane. Defaults to world XY. |
| `revolve(profile: Profile, *, axis_direction: Point3D, axis_origin: Point3D = (0.0, 0.0, 0.0), angle_deg: float = 360.0, plane: Plane = Plane()) -> Shape` | Revolves a single-boundary profile around an axis in its placement plane. Angle is greater than zero and at most 360 degrees. |
| `loft(sections: Iterable[tuple[Profile, Plane]] \| Iterable[Path3D], /, *, degree: int = 1) -> Shape` | Caps a solid through placed profiles or through closed spatial paths with corresponding curves. Sections must be planar and without holes. `degree` is the polynomial degree in the direction through the sections. |
| `sweep(profile: Profile, path: Path3D, /, *, plane: Plane) -> Shape` | Sweeps a profile, including any holes, from the start of the path. Sharp polyline corners are mitred. |

Primitives share one convention: centred in local XY with the base at
z = 0. Position them with `place`, `translate`, `rotate`, or `mirror`.
`loft` has two typed overloads, one for `(Profile, Plane)` pairs and one for
`Path3D` sections.

## Transformations and booleans

| Signature | Behavior |
| --- | --- |
| `translate(shape: Shape, *, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Shape` | Moves a copy by signed offsets along the world axes. |
| `rotate(shape: Shape, *, axis_direction: Point3D, angle_deg: float, axis_origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Rotates a copy about the line through `axis_origin` in the nonzero direction `axis_direction`. Positive angles follow the right-hand rule. |
| `mirror(shape: Shape, *, normal: Point3D, origin: Point3D = (0.0, 0.0, 0.0)) -> Shape` | Reflects a copy across the plane through `origin` with the specified normal. |
| `union(shape: Shape, /, *shapes: Shape) -> Shape` | Material in any operand. `union(*parts)` combines many shapes in one kernel operation. `left + right` unites two. |
| `intersection(left: Shape, right: Shape, /) -> Shape \| None` | Material in both operands. Returns `None` if empty. `left & right` is the same operation but raises `EmptyResultError` instead. |
| `difference(left: Shape, right: Shape, /) -> Shape \| None` | Material in `left` after removing `right`. Returns `None` if empty. `left - right` is the same operation but raises `EmptyResultError` (a `ValueError` subclass) instead, so chained subtraction never yields `None`. |

## Topology and finishing

A `Face` or `Edge` retains a reference to the exact `Shape` object it came
from. Edges returned by `edges(face)` belong to that same shape and can be
used with `fillet()` or `chamfer()`. After an operation creates a new shape,
query that result for its own edge references. Faces, edges, and vertices
compare equal and hash alike when they name the same entity of the same
shape object, so sets and `in` work across queries. `fillet()` and
`chamfer()` treat repeated references to one edge as a single edge.

Topology references expose read-only data for filtering with ordinary
Python, for example
`[e for e in edges(plate) if e.line_direction and abs(e.line_direction[2]) == 1]`
for the edges parallel to Z.

| Attribute | Value |
| --- | --- |
| `Face.kind` | `FaceKind`: `"plane"`, `"cylinder"`, `"cone"`, `"sphere"`, `"torus"`, `"spline"`, `"revolution"`, or `"blend"`. A round on a straight edge is a `"cylinder"`; the corner of three rounds is a `"sphere"`. Surfaces from `revolve`, `loft`, and `sweep` are often stored as `"spline"`. |
| `Face.area` | Area in square millimetres. |
| `Face.centroid` | Area centroid. |
| `Face.planar_normal` | Outward unit normal of a planar face, else `None`. |
| `Edge.kind` | `EdgeKind`: `"line"`, `"circle"`, `"ellipse"`, `"polyline"`, `"spline"`, or `"intersection"`. |
| `Edge.start`, `Edge.end` | Endpoints in the edge's direction; equal for a closed edge. |
| `Edge.line_direction` | Unit vector from `start` to `end` for a line edge, else `None`. Its sign follows the edge's direction; axis-aligned values are exact. |
| `Edge.circle_center`, `Edge.circle_radius` | For circles and arcs, else `None`. |
| `Edge.length` | Trimmed length in millimetres. |
| `Vertex.point` | XYZ position. |

`EdgeKind` and `FaceKind` are `Literal` string types: kinds are plain strings
at runtime, and a type checker rejects a misspelled comparison such as
`face.kind == "cylindre"`.

| Signature | Behavior |
| --- | --- |
| `faces(scope: Shape \| Edge, /) -> tuple[Face, ...]` | Returns read-only faces of a shape or unique faces incident to an edge. |
| `edges(scope: Shape \| Face, /) -> tuple[Edge, ...]` | Returns read-only edges of a shape or the unique boundary edges of a face, including hole rims. |
| `vertices(scope: Shape \| Face \| Edge, /) -> tuple[Vertex, ...]` | Returns unique topological vertices, including vertices on face holes. |
| `fillet(shape: Shape, edges: Iterable[Edge], /, *, radius: float) -> Shape` | Rounds selected edges on a copy. The references must come from this exact shape. |
| `chamfer(shape: Shape, edges: Iterable[Edge], /, *, setback: float) -> Shape` | Bevels selected edges on a copy with equal setbacks along the adjacent faces. The references must come from this exact shape. |
| `shell(shape: Shape, open_faces: Iterable[Face], /, *, thickness: float, side: Literal["inward", "outward"] = "inward") -> Shape` | Hollows a copy into a wall of constant positive `thickness`, removing `open_faces`. With no open faces the result is closed around an inner void. `"inward"` keeps the outer size; `"outward"` grows the shape, with sharp corners on a box. The references must come from this exact shape. |

## Measurement and STEP exchange

| Signature | Behavior |
| --- | --- |
| `bounds(shape: Shape) -> Bounds` | Returns the world-axis-aligned bounding box. |
| `volume(shape: Shape, *, relative_tolerance: float = 1e-9) -> float` | Returns enclosed volume. The requested relative integration tolerance is positive and dimensionless. |
| `area(shape: Shape, *, relative_tolerance: float = 1e-9) -> float` | Returns the surface area in square millimetres, every face counted once. |
| `centroid(shape: Shape, *, relative_tolerance: float = 1e-9) -> Point3D` | Returns the centroid of the volume, the centre of mass at uniform density. Unlike `bounds(shape).center`, it depends on where the material is. |
| `import_step(path: str \| PathLike[str], /) -> Shape` | Reads a STEP file and merges all closed solids into one shape, placed in world coordinates. Part identity is not kept. |
| `export_step(shape: Shape, path: str \| PathLike[str], *, name: str = "Part") -> None` | Writes STEP AP242, using `name` as the part label. Overwrites an existing file. |

Invalid argument values can raise `ValueError`. The operators `-` and `&`
raise `EmptyResultError`, a `ValueError` subclass, when their result would be
empty; `difference()` and `intersection()` return `None` instead.
Kernel failures raise `KernelError` (a `RuntimeError` subclass). Filesystem errors from STEP exchange
propagate as `OSError` subclasses.


## Visualization

| Signature | Behavior |
| --- | --- |
| `tessellate(shape: Shape, /, *, chord_tolerance: float \| None = None) -> Mesh` | Uses SolidCore to approximate a shape with triangles and CAD outlines. Chord tolerance is a positive target deviation in millimetres and defaults to a value based on the shape's size. |
| `solidfunc.view.show(shape: Shape, /, *, chord_tolerance: float \| None = None, screenshot: str \| PathLike[str] \| None = None, jupyter_backend: str = "static") -> None` | Uses optional PyVista to display a part or save a PNG. In Jupyter the default is static. Install `pyvista[jupyter]` for the interactive `"client"` backend. |

A `Shape` that ends a notebook cell displays itself through
`_repr_mimebundle_`, with no extra Python packages. The bundle has the
shape's `repr`, a static isometric SVG, and HTML that replaces
the SVG with an interactive view once the browser has loaded
[vtk.js](https://github.com/Kitware/vtk-js) (a pinned version, from
cdn.jsdelivr.net). Frontends that don't run scripts, or have no internet
access, show the SVG.
