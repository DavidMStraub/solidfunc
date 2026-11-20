"""Check the plain-text reprs of solidfunc's opaque types."""

import solidfunc as sf


def plate() -> sf.Shape:
    return sf.box(size_x=80, size_y=50, size_z=10) - sf.cylinder(diameter=20, height=10)


def test_shape_repr_counts_faces_and_edges() -> None:
    shape = plate()
    assert repr(shape) == (
        f"<Shape: {len(sf.faces(shape))} faces, {len(sf.edges(shape))} edges>"
    )


def test_face_repr_shows_kind_and_planar_normal() -> None:
    faces = sf.faces(plate())
    top = max(faces, key=lambda face: face.centroid[2])
    assert repr(top) == "<Face plane, normal (0, 0, 1)>"
    wall = next(face for face in faces if face.kind == "cylinder")
    assert repr(wall) == "<Face cylinder>"


def test_edge_and_vertex_reprs_show_points() -> None:
    box = sf.box(size_x=2, size_y=2, size_z=1)
    line = next(edge for edge in sf.edges(box) if edge.kind == "line")
    assert repr(line).startswith("<Edge line, (")
    rim = next(edge for edge in sf.edges(plate()) if edge.kind == "circle")
    assert repr(rim).startswith("<Edge circle r=10, (")
    assert {repr(vertex) for vertex in sf.vertices(box)} >= {
        "<Vertex (-1, -1, 0)>",
        "<Vertex (1, 1, 1)>",
    }


def test_planar_reprs() -> None:
    assert repr(sf.line((0, 0), (10, 0.5))) == "<Curve2D line, (0, 0) to (10, 0.5)>"
    assert repr(sf.circle(radius=5)).startswith("<Curve2D arc r=5, ")
    assert repr(sf.rectangle(size_x=4, size_y=2)) == "<Path2D closed, 4 curves>"
    assert repr(sf.polyline([(0, 0), (1, 0), (1, 1)])) == "<Path2D open, 2 curves>"
    assert repr(sf.profile(sf.circle(radius=5))) == "<Profile>"
    holed = sf.profile(sf.circle(radius=5), holes=[sf.circle(radius=1)])
    assert repr(holed) == "<Profile with 1 hole>"


def test_path3d_repr() -> None:
    path = sf.polyline3d([(0, 0, 0), (10, 0, 0), (10, 10, 0)])
    assert repr(path) == "<Path3D open, 2 curves>"
