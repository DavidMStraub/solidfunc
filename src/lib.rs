//! Small, private bindings to SolidCore's application operations.
//!
//! Public functions and argument conventions live in the Python package. Bodies never expose
//! a mutating method to Python; a transformation copies its input before editing the copy.

use pyo3::create_exception;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use solidcore_ops::{affine, Body, BooleanOp, Error, Result};
use solidcore_step::write::product::{solidcore_bodies, Header};

mod modeling;
mod planar;
mod step_import;
mod topology;

create_exception!(_core, KernelError, PyRuntimeError);

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

    fn __sub__(&self, py: Python<'_>, other: &Shape) -> PyResult<Option<Shape>> {
        _difference(py, self, other)
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
    module.add_function(wrap_pyfunction!(_box, module)?)?;
    module.add_function(wrap_pyfunction!(_cylinder, module)?)?;
    module.add_function(wrap_pyfunction!(_union, module)?)?;
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
    planar::register(module)
}
