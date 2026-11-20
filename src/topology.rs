//! Shape-scoped topology references and edge blending.

use std::collections::BTreeSet;
use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use solidcore_ops::blend::{blend_ordered, Blend, BlendOptions, Corners};
use solidcore_ops::Order;
use solidcore_record::brep::{Brep, Curve, Loop};

use crate::{kernel_error, Shape};

type Point = (f64, f64, f64);

/// An edge of the shape from which it was queried.
#[pyclass(frozen, module = "solidfunc")]
struct Edge {
    owner: Py<Shape>,
    order: Arc<Order>,
    index: usize,
    #[pyo3(get)]
    kind: &'static str,
    #[pyo3(get)]
    circle_center: Option<Point>,
    #[pyo3(get)]
    circle_radius: Option<f64>,
}

fn owner_key(owner: &Py<Shape>) -> usize {
    owner.as_ptr() as usize
}

fn hash_key(key: (usize, u32)) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    key.hash(&mut hasher);
    hasher.finish()
}

impl Edge {
    fn key(&self) -> (usize, u32) {
        (owner_key(&self.owner), self.order.edges[self.index].index())
    }

    fn new(owner: Py<Shape>, order: Arc<Order>, index: usize, curve: Curve) -> Self {
        let (kind, circle_center, circle_radius) = match curve {
            Curve::Line { .. } => ("line", None, None),
            Curve::Circle { frame, radius } => ("circle", Some(frame.origin.into()), Some(radius)),
            Curve::Ellipse { .. } => ("ellipse", None, None),
            Curve::Polyline { .. } => ("polyline", None, None),
            Curve::Spline { .. } | Curve::RationalSpline { .. } => ("spline", None, None),
            Curve::SurfaceIntersection { .. } => ("intersection", None, None),
        };
        Self {
            owner,
            order,
            index,
            kind,
            circle_center,
            circle_radius,
        }
    }
}

#[pymethods]
impl Edge {
    fn __eq__(&self, other: PyRef<'_, Self>) -> bool {
        self.key() == other.key()
    }

    fn __hash__(&self) -> u64 {
        hash_key(self.key())
    }

    /// Edge length in millimetres.
    #[getter]
    fn length(&self, py: Python<'_>) -> PyResult<f64> {
        let shape = self.owner.get();
        py.detach(|| shape.body.edge_length(&self.order, self.index, 1e-9))
            .map_err(|error| kernel_error("edge length", error))
    }
}

/// A face of the shape from which it was queried.
#[pyclass(frozen, module = "solidfunc")]
struct Face {
    owner: Py<Shape>,
    order: Arc<Order>,
    index: usize,
}

impl Face {
    fn key(&self) -> (usize, u32) {
        (owner_key(&self.owner), self.order.faces[self.index].index())
    }
}

#[pymethods]
impl Face {
    fn __eq__(&self, other: PyRef<'_, Self>) -> bool {
        self.key() == other.key()
    }

    fn __hash__(&self) -> u64 {
        hash_key(self.key())
    }

    /// Area centroid in world millimetres.
    #[getter]
    fn center(&self, py: Python<'_>) -> PyResult<Point> {
        let shape = self.owner.get();
        py.detach(|| shape.body.face_centroid(&self.order, self.index, 1e-9))
            .map(|result| result.centroid.into())
            .map_err(|error| kernel_error("face center", error))
    }

    /// Outward unit normal for a planar face, or None for a curved face.
    #[getter]
    fn normal(&self, py: Python<'_>) -> PyResult<Option<Point>> {
        let shape = self.owner.get();
        py.detach(|| shape.body.face_plane_normal(&self.order, self.index))
            .map(|result| result.map(|normal| normal.value.into()))
            .map_err(|error| kernel_error("face normal", error))
    }
}

#[pyfunction]
fn _edges<'py>(py: Python<'py>, shape: Py<Shape>) -> PyResult<Bound<'py, PyTuple>> {
    let (record, order) = py
        .detach(|| shape.get().body.to_record())
        .map_err(|error| kernel_error("edges", error))?;
    let order = Arc::new(order);
    PyTuple::new(
        py,
        record.edges.into_iter().enumerate().map(|(index, edge)| {
            Edge::new(shape.clone_ref(py), Arc::clone(&order), index, edge.curve)
        }),
    )
}

#[pyfunction]
fn _face_edges<'py>(py: Python<'py>, face: &Face) -> PyResult<Bound<'py, PyTuple>> {
    let shape = face.owner.get();
    let (record, order, indices) = py
        .detach(|| {
            let (record, order) = shape.body.to_record()?;
            let index = record_index(&order.faces, &face.order.faces, face.index)?;
            let indices: BTreeSet<_> = record.faces[index]
                .loops
                .iter()
                .flat_map(|boundary| match boundary {
                    Loop::Edges { edges } => edges.as_slice(),
                    Loop::Vertex { .. } => &[],
                })
                .map(|edge| edge.edge as usize)
                .collect();
            Ok((record, Arc::new(order), indices))
        })
        .map_err(|error| kernel_error("edges", error))?;

    let boundary_edges: Vec<_> = record
        .edges
        .into_iter()
        .enumerate()
        .filter(|(index, _)| indices.contains(index))
        .map(|(index, edge)| {
            Edge::new(
                face.owner.clone_ref(py),
                Arc::clone(&order),
                index,
                edge.curve,
            )
        })
        .collect();
    PyTuple::new(py, boundary_edges)
}

#[pyfunction]
fn _faces<'py>(py: Python<'py>, shape: Py<Shape>) -> PyResult<Bound<'py, PyTuple>> {
    let (_, order) = py
        .detach(|| shape.get().body.to_record())
        .map_err(|error| kernel_error("faces", error))?;
    let order = Arc::new(order);
    PyTuple::new(
        py,
        (0..order.faces.len()).map(|index| Face {
            owner: shape.clone_ref(py),
            order: Arc::clone(&order),
            index,
        }),
    )
}

/// A read-only vertex position in world millimetres.
#[pyclass(frozen, module = "solidfunc")]
struct Vertex {
    owner: Py<Shape>,
    id: u32,
    #[pyo3(get)]
    point: Point,
}

#[pymethods]
impl Vertex {
    fn __eq__(&self, other: PyRef<'_, Self>) -> bool {
        self.key() == other.key()
    }

    fn __hash__(&self) -> u64 {
        hash_key(self.key())
    }
}

impl Vertex {
    fn key(&self) -> (usize, u32) {
        (owner_key(&self.owner), self.id)
    }
}

fn record_index<T: PartialEq>(
    items: &[T],
    original: &[T],
    index: usize,
) -> solidcore_ops::Result<usize> {
    let id = &original[index];
    if items.get(index) == Some(id) {
        return Ok(index);
    }
    items
        .iter()
        .position(|item| item == id)
        .ok_or(solidcore_ops::Error::Argument)
}

fn vertex_refs<'py>(
    py: Python<'py>,
    owner: &Py<Shape>,
    record: &Brep,
    order: &Order,
    indices: impl IntoIterator<Item = usize>,
) -> PyResult<Bound<'py, PyTuple>> {
    let vertices = indices
        .into_iter()
        .map(|index| Vertex {
            owner: owner.clone_ref(py),
            id: order.vertices[index].index(),
            point: record.vertices[index].point.into(),
        })
        .collect::<Vec<_>>();
    PyTuple::new(py, vertices)
}

#[pyfunction]
fn _edge_faces<'py>(py: Python<'py>, edge: &Edge) -> PyResult<Bound<'py, PyTuple>> {
    let (order, indices) = py
        .detach(|| {
            let (record, order) = edge.owner.get().body.to_record()?;
            let index = record_index(&order.edges, &edge.order.edges, edge.index)?;
            let indices: BTreeSet<_> = record.edges[index]
                .uses
                .iter()
                .map(|usage| usage.face as usize)
                .collect();
            Ok((Arc::new(order), indices))
        })
        .map_err(|error| kernel_error("faces", error))?;
    PyTuple::new(
        py,
        indices.into_iter().map(|index| Face {
            owner: edge.owner.clone_ref(py),
            order: Arc::clone(&order),
            index,
        }),
    )
}

#[pyfunction]
fn _vertices<'py>(py: Python<'py>, shape: Py<Shape>) -> PyResult<Bound<'py, PyTuple>> {
    let (record, order) = py
        .detach(|| shape.get().body.to_record())
        .map_err(|error| kernel_error("vertices", error))?;
    vertex_refs(py, &shape, &record, &order, 0..record.vertices.len())
}

#[pyfunction]
fn _face_vertices<'py>(py: Python<'py>, face: &Face) -> PyResult<Bound<'py, PyTuple>> {
    let (record, order, indices) = py
        .detach(|| {
            let (record, order) = face.owner.get().body.to_record()?;
            let index = record_index(&order.faces, &face.order.faces, face.index)?;
            let mut indices = BTreeSet::new();
            for boundary in &record.faces[index].loops {
                match boundary {
                    Loop::Edges { edges } => {
                        for usage in edges {
                            indices.extend(
                                record.edges[usage.edge as usize]
                                    .vertices
                                    .map(|v| v as usize),
                            );
                        }
                    }
                    Loop::Vertex { vertex } => {
                        indices.insert(*vertex as usize);
                    }
                }
            }
            Ok((record, order, indices))
        })
        .map_err(|error| kernel_error("vertices", error))?;
    vertex_refs(py, &face.owner, &record, &order, indices)
}

#[pyfunction]
fn _edge_vertices<'py>(py: Python<'py>, edge: &Edge) -> PyResult<Bound<'py, PyTuple>> {
    let (record, order, indices) = py
        .detach(|| {
            let (record, order) = edge.owner.get().body.to_record()?;
            let index = record_index(&order.edges, &edge.order.edges, edge.index)?;
            let indices = BTreeSet::from(record.edges[index].vertices.map(|v| v as usize));
            Ok((record, order, indices))
        })
        .map_err(|error| kernel_error("vertices", error))?;
    vertex_refs(py, &edge.owner, &record, &order, indices)
}

fn finish_edges(
    py: Python<'_>,
    shape: Py<Shape>,
    edges: Vec<PyRef<'_, Edge>>,
    size: f64,
    kind: Blend,
    operation: &str,
) -> PyResult<Shape> {
    if edges
        .iter()
        .any(|edge| !edge.owner.bind(py).is(shape.bind(py)))
    {
        return Err(PyValueError::new_err(format!(
            "{operation} edges must belong to the supplied shape"
        )));
    }
    // The same topological edge can arrive through several queries; blend it once.
    let mut seen = BTreeSet::new();
    let indices: Vec<_> = edges
        .iter()
        .map(|edge| edge.order.edges[edge.index])
        .filter(|id| seen.insert(*id))
        .collect();
    let shape = shape.get();
    py.detach(|| {
        let (_, order) = shape.body.to_record()?;
        let indices = indices
            .iter()
            .map(|id| {
                order
                    .edges
                    .iter()
                    .position(|edge| edge == id)
                    .ok_or(solidcore_ops::Error::Argument)
            })
            .collect::<solidcore_ops::Result<Vec<_>>>()?;
        let (body, order) = shape.body.copy_with_order(&order)?;
        blend_ordered(
            &body,
            &order,
            kind,
            &indices,
            &[size],
            &[],
            Corners::Filled,
            BlendOptions::default(),
        )?;
        Ok(Shape { body })
    })
    .map_err(|error| kernel_error(operation, error))
}

#[pyfunction]
fn _fillet(
    py: Python<'_>,
    shape: Py<Shape>,
    edges: Vec<PyRef<'_, Edge>>,
    radius: f64,
) -> PyResult<Shape> {
    finish_edges(py, shape, edges, radius, Blend::Round, "fillet")
}

#[pyfunction]
fn _chamfer(
    py: Python<'_>,
    shape: Py<Shape>,
    edges: Vec<PyRef<'_, Edge>>,
    distance: f64,
) -> PyResult<Shape> {
    finish_edges(py, shape, edges, distance, Blend::Chamfer, "chamfer")
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Edge>()?;
    module.add_class::<Face>()?;
    module.add_class::<Vertex>()?;
    module.add_function(wrap_pyfunction!(_edges, module)?)?;
    module.add_function(wrap_pyfunction!(_face_edges, module)?)?;
    module.add_function(wrap_pyfunction!(_faces, module)?)?;
    module.add_function(wrap_pyfunction!(_edge_faces, module)?)?;
    module.add_function(wrap_pyfunction!(_vertices, module)?)?;
    module.add_function(wrap_pyfunction!(_face_vertices, module)?)?;
    module.add_function(wrap_pyfunction!(_edge_vertices, module)?)?;
    module.add_function(wrap_pyfunction!(_fillet, module)?)?;
    module.add_function(wrap_pyfunction!(_chamfer, module)?)?;
    Ok(())
}
