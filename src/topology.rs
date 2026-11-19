//! Shape-scoped topology references and edge blending.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use solidcore_ops::blend::{blend_ordered, Blend, BlendOptions, Corners};
use solidcore_ops::Order;
use solidcore_record::brep::Curve;

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

#[pymethods]
impl Edge {
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

#[pymethods]
impl Face {
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
            let (kind, circle_center, circle_radius) = match edge.curve {
                Curve::Line { .. } => ("line", None, None),
                Curve::Circle { frame, radius } => {
                    ("circle", Some(frame.origin.into()), Some(radius))
                }
                Curve::Ellipse { .. } => ("ellipse", None, None),
                Curve::Polyline { .. } => ("polyline", None, None),
                Curve::Spline { .. } | Curve::RationalSpline { .. } => ("spline", None, None),
                Curve::SurfaceIntersection { .. } => ("intersection", None, None),
            };
            Edge {
                owner: shape.clone_ref(py),
                order: Arc::clone(&order),
                index,
                kind,
                circle_center,
                circle_radius,
            }
        }),
    )
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
    let indices: Vec<_> = edges
        .iter()
        .map(|edge| edge.order.edges[edge.index])
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
    module.add_function(wrap_pyfunction!(_edges, module)?)?;
    module.add_function(wrap_pyfunction!(_faces, module)?)?;
    module.add_function(wrap_pyfunction!(_fillet, module)?)?;
    module.add_function(wrap_pyfunction!(_chamfer, module)?)?;
    Ok(())
}
