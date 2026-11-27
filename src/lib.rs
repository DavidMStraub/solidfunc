//! Small, private bindings to SolidCore's application operations.
//!
//! Public functions and argument conventions live in the Python package. Bodies never expose
//! a mutating method to Python; a transformation copies its input before editing the copy.

use pyo3::create_exception;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use solidcore_ops::{affine, Body, BooleanOp, Error, Result};
use solidcore_step::write::product::{solidcore_bodies, Header};

mod mesh;
mod modeling;
mod planar;
mod step_import;
mod topology;

create_exception!(_core, KernelError, PyRuntimeError);
create_exception!(_core, EmptyResultError, PyValueError);

/// An opaque shape created by solidfunc's construction functions.
#[pyclass(frozen, module = "solidfunc")]
struct Shape {
    body: Body,
}

#[pymethods]
impl Shape {
    fn __add__(&self, py: Python<'_>, other: &Shape) -> PyResult<Shape> {
        _union(py, self, other)
    }

    /// Intersect like `intersection`, but raise `EmptyResultError` when the operands share no
    /// material.
    fn __and__(&self, py: Python<'_>, other: &Shape) -> PyResult<Shape> {
        _intersection(py, self, other)?.ok_or_else(|| {
            EmptyResultError::new_err(
                "intersection found no shared material; use intersection() to receive None instead",
            )
        })
    }

    /// Subtract like `difference`, but raise `EmptyResultError` when no material remains,
    /// so chained subtraction never yields `None`.
    fn __sub__(&self, py: Python<'_>, other: &Shape) -> PyResult<Shape> {
        _difference(py, self, other)?.ok_or_else(|| {
            EmptyResultError::new_err(
                "subtraction removed all material; use difference() to receive None instead",
            )
        })
    }

    /// Face and edge counts. Bounds and volume would cost a kernel computation.
    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let (record, _) = py
            .detach(|| self.body.to_record())
            .map_err(|error| kernel_error("repr", error))?;
        Ok(format!(
            "<Shape: {}, {}>",
            repr_count(record.faces.len(), "face"),
            repr_count(record.edges.len(), "edge")
        ))
    }

    /// The `__cad_interface__` protocol, delegated to `solidfunc._interface`.
    #[pyo3(signature = (*, accept=None))]
    fn __cad_interface__<'py>(
        slf: &Bound<'py, Self>,
        accept: Option<Bound<'py, PyAny>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        slf.py()
            .import("solidfunc._interface")?
            .call_method1("_cad_interface", (slf, accept))
    }

    /// Notebook display, delegated to `solidfunc._display`.
    #[pyo3(signature = (include=None, exclude=None))]
    fn _repr_mimebundle_<'py>(
        slf: &Bound<'py, Self>,
        include: Option<Bound<'py, PyAny>>,
        exclude: Option<Bound<'py, PyAny>>,
    ) -> PyResult<Bound<'py, PyAny>> {
        slf.py()
            .import("solidfunc._display")?
            .call_method1("mimebundle", (slf, include, exclude))
    }
}

/// A coordinate for a `__repr__`: at most four decimals, without trailing zeros or `-0`.
fn repr_number(value: f64) -> String {
    let text = format!("{value:.4}");
    let text = text.trim_end_matches('0').trim_end_matches('.');
    if text == "-0" {
        "0".into()
    } else {
        text.into()
    }
}

/// A point for a `__repr__`, such as `(10, 0, 2.5)`.
fn repr_point(coordinates: &[f64]) -> String {
    let parts: Vec<_> = coordinates.iter().copied().map(repr_number).collect();
    format!("({})", parts.join(", "))
}

/// `"1 face"` or `"3 faces"`.
fn repr_count(count: usize, noun: &str) -> String {
    if count == 1 {
        format!("1 {noun}")
    } else {
        format!("{count} {noun}s")
    }
}

fn kernel_error(operation: &str, error: Error) -> PyErr {
    let message = format!("{operation}: {error}");
    match error {
        Error::Argument => PyValueError::new_err(message),
        _ => KernelError::new_err(message),
    }
}

#[pyfunction]
fn _box(py: Python<'_>, origin: [f64; 3], size: [f64; 3]) -> PyResult<Shape> {
    py.detach(|| solidcore_ops::make_box(origin, size))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("box", error))
}

#[pyfunction]
fn _cylinder(py: Python<'_>, origin: [f64; 3], radius: f64, height: f64) -> PyResult<Shape> {
    py.detach(|| solidcore_ops::make_cylinder(origin, radius, height))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("cylinder", error))
}

#[pyfunction]
fn _sphere(py: Python<'_>, center: [f64; 3], radius: f64) -> PyResult<Shape> {
    py.detach(|| solidcore_ops::make_sphere(center, radius))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("sphere", error))
}

#[pyfunction]
fn _cone(
    py: Python<'_>,
    origin: [f64; 3],
    base_radius: f64,
    top_radius: f64,
    height: f64,
) -> PyResult<Shape> {
    py.detach(|| solidcore_ops::make_cone(origin, base_radius, top_radius, height))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("cone", error))
}

#[pyfunction]
fn _torus(
    py: Python<'_>,
    center: [f64; 3],
    major_radius: f64,
    minor_radius: f64,
) -> PyResult<Shape> {
    py.detach(|| solidcore_ops::make_torus(center, major_radius, minor_radius))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("torus", error))
}

fn boolean_result(
    py: Python<'_>,
    left: &Shape,
    right: &Shape,
    operation: BooleanOp,
    name: &str,
) -> PyResult<Option<Shape>> {
    py.detach(|| {
        // The kernel consumes both operands, including on failure. Copy even when they alias.
        let left = left.body.copy()?;
        let right = right.body.copy()?;
        solidcore_ops::boolean::boolean(left, right, operation)
    })
    .map(|result| result.map(|body| Shape { body }))
    .map_err(|error| kernel_error(name, error))
}

#[pyfunction]
fn _union(py: Python<'_>, left: &Shape, right: &Shape) -> PyResult<Shape> {
    boolean_result(py, left, right, BooleanOp::Union, "union")?
        .ok_or_else(|| kernel_error("union", Error::Empty))
}

#[pyfunction]
fn _union_all(py: Python<'_>, shapes: Vec<PyRef<'_, Shape>>) -> PyResult<Shape> {
    let bodies: Vec<&Body> = shapes.iter().map(|shape| &shape.body).collect();
    py.detach(|| {
        // The kernel consumes its operands; copy so the inputs stay unchanged.
        let copies = bodies
            .iter()
            .map(|body| body.copy())
            .collect::<Result<Vec<_>>>()?;
        solidcore_ops::boolean::union_all(copies)
    })
    .map(|body| Shape { body })
    .map_err(|error| kernel_error("union", error))
}

#[pyfunction]
fn _intersection(py: Python<'_>, left: &Shape, right: &Shape) -> PyResult<Option<Shape>> {
    boolean_result(py, left, right, BooleanOp::Intersect, "intersection")
}

#[pyfunction]
fn _difference(py: Python<'_>, left: &Shape, right: &Shape) -> PyResult<Option<Shape>> {
    boolean_result(py, left, right, BooleanOp::Subtract, "difference")
}

#[pyfunction]
fn _volume(py: Python<'_>, shape: &Shape, relative_accuracy: f64) -> PyResult<f64> {
    py.detach(|| shape.body.volume(relative_accuracy))
        .map_err(|error| kernel_error("volume", error))
}

#[pyfunction]
fn _area(py: Python<'_>, shape: &Shape, relative_accuracy: f64) -> PyResult<f64> {
    py.detach(|| shape.body.area(relative_accuracy))
        .map_err(|error| kernel_error("area", error))
}

/// The centre of the shape's volume (its centre of mass at uniform density).
#[pyfunction]
fn _centroid(py: Python<'_>, shape: &Shape, relative_accuracy: f64) -> PyResult<[f64; 3]> {
    py.detach(|| shape.body.mass_properties(relative_accuracy))
        .map(|estimate| estimate.centroid)
        .map_err(|error| kernel_error("centroid", error))
}

fn transformed(shape: &Shape, matrix: &affine::Matrix) -> Result<Shape> {
    let body = shape.body.copy()?;
    body.transform(matrix)?;
    Ok(Shape { body })
}

#[pyfunction]
fn _translate(py: Python<'_>, shape: &Shape, offset: [f64; 3]) -> PyResult<Shape> {
    py.detach(|| transformed(shape, &affine::translation(offset)?))
        .map_err(|error| kernel_error("translate", error))
}

#[pyfunction]
fn _rotate(
    py: Python<'_>,
    shape: &Shape,
    origin: [f64; 3],
    axis: [f64; 3],
    angle: f64,
) -> PyResult<Shape> {
    py.detach(|| transformed(shape, &affine::rotation(origin, axis, angle)?))
        .map_err(|error| kernel_error("rotate", error))
}

/// Map world coordinates onto a frame: the origin to `origin` and the X, Y, and Z axes to
/// the given orthonormal directions.
#[pyfunction]
fn _place(
    py: Python<'_>,
    shape: &Shape,
    origin: [f64; 3],
    x: [f64; 3],
    y: [f64; 3],
    z: [f64; 3],
) -> PyResult<Shape> {
    let row = |[a, b, c]: [f64; 3], w: f64| [a, b, c, w];
    let matrix = [row(x, 0.0), row(y, 0.0), row(z, 0.0), row(origin, 1.0)];
    py.detach(|| transformed(shape, &matrix))
        .map_err(|error| kernel_error("place", error))
}

#[pyfunction]
fn _mirror(py: Python<'_>, shape: &Shape, origin: [f64; 3], normal: [f64; 3]) -> PyResult<Shape> {
    py.detach(|| transformed(shape, &affine::reflection(origin, normal)?))
        .map_err(|error| kernel_error("mirror", error))
}

#[pyfunction]
fn _bounds(py: Python<'_>, shape: &Shape) -> PyResult<([f64; 3], [f64; 3])> {
    py.detach(|| shape.body.bounds())
        .map_err(|error| kernel_error("bounds", error))
}

#[pyfunction]
fn _step_text(py: Python<'_>, shape: &Shape, file_name: &str, name: &str) -> PyResult<String> {
    py.detach(|| {
        let header = Header {
            file_name: file_name.to_owned(),
            originating_system: "solidfunc".to_owned(),
            preprocessor_version: format!("solidfunc {}", env!("CARGO_PKG_VERSION")),
            ..Header::default()
        };
        solidcore_bodies(&[(name, &shape.body)], &header)
    })
    .map_err(|error| KernelError::new_err(format!("export_step: {error}")))
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Shape>()?;
    module.add("KernelError", module.py().get_type::<KernelError>())?;
    module.add(
        "EmptyResultError",
        module.py().get_type::<EmptyResultError>(),
    )?;
    module.add_function(wrap_pyfunction!(_box, module)?)?;
    module.add_function(wrap_pyfunction!(_cylinder, module)?)?;
    module.add_function(wrap_pyfunction!(_sphere, module)?)?;
    module.add_function(wrap_pyfunction!(_cone, module)?)?;
    module.add_function(wrap_pyfunction!(_torus, module)?)?;
    module.add_function(wrap_pyfunction!(_area, module)?)?;
    module.add_function(wrap_pyfunction!(_centroid, module)?)?;
    module.add_function(wrap_pyfunction!(_union, module)?)?;
    module.add_function(wrap_pyfunction!(_union_all, module)?)?;
    module.add_function(wrap_pyfunction!(_place, module)?)?;
    module.add_function(wrap_pyfunction!(_intersection, module)?)?;
    module.add_function(wrap_pyfunction!(_difference, module)?)?;
    module.add_function(wrap_pyfunction!(_volume, module)?)?;
    module.add_function(wrap_pyfunction!(_translate, module)?)?;
    module.add_function(wrap_pyfunction!(_rotate, module)?)?;
    module.add_function(wrap_pyfunction!(_bounds, module)?)?;
    module.add_function(wrap_pyfunction!(_step_text, module)?)?;
    module.add_function(wrap_pyfunction!(_mirror, module)?)?;
    step_import::register(module)?;
    topology::register(module)?;
    modeling::register(module)?;
    mesh::register(module)?;
    planar::register(module)
}
