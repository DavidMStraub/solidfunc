//! Small, private bindings to SolidCore's application operations.
//!
//! Public functions and argument conventions live in the Python package. Bodies never expose
//! a mutating method to Python; a transformation copies its input before editing the copy.

use pyo3::create_exception;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use solidcore_ops::{affine, Body, BooleanOp, Error};
use solidcore_step::write::product::{solidcore_bodies, Header};

create_exception!(_core, SolidCoreError, PyRuntimeError);

/// An opaque solid created by solidfunc's construction functions.
#[pyclass(frozen, module = "solidfunc")]
struct Solid {
    body: Body,
}

fn kernel_error(operation: &str, error: Error) -> PyErr {
    let message = format!("{operation}: {error}");
    match error {
        Error::Argument => PyValueError::new_err(message),
        _ => SolidCoreError::new_err(message),
    }
}

#[pyfunction]
fn _box(py: Python<'_>, origin: [f64; 3], size: [f64; 3]) -> PyResult<Solid> {
    py.detach(|| solidcore_ops::make_box(origin, size))
        .map(|body| Solid { body })
        .map_err(|error| kernel_error("box", error))
}

#[pyfunction]
fn _cylinder(py: Python<'_>, origin: [f64; 3], radius: f64, height: f64) -> PyResult<Solid> {
    py.detach(|| solidcore_ops::make_cylinder(origin, radius, height))
        .map(|body| Solid { body })
        .map_err(|error| kernel_error("cylinder", error))
}

fn boolean_result(
    py: Python<'_>,
    left: &Solid,
    right: &Solid,
    operation: BooleanOp,
    name: &str,
) -> PyResult<Option<Solid>> {
    py.detach(|| {
        // The kernel consumes both operands, including on failure. Copy even when they alias.
        let left = left.body.copy()?;
        let right = right.body.copy()?;
        solidcore_ops::boolean::boolean(left, right, operation)
    })
    .map(|result| result.map(|body| Solid { body }))
    .map_err(|error| kernel_error(name, error))
}

#[pyfunction]
fn _union(py: Python<'_>, left: &Solid, right: &Solid) -> PyResult<Solid> {
    boolean_result(py, left, right, BooleanOp::Union, "union")?
        .ok_or_else(|| kernel_error("union", Error::Empty))
}

#[pyfunction]
fn _intersection(py: Python<'_>, left: &Solid, right: &Solid) -> PyResult<Option<Solid>> {
    boolean_result(py, left, right, BooleanOp::Intersect, "intersection")
}

#[pyfunction]
fn _difference(py: Python<'_>, left: &Solid, right: &Solid) -> PyResult<Option<Solid>> {
    boolean_result(py, left, right, BooleanOp::Subtract, "difference")
}

#[pyfunction]
fn _volume(py: Python<'_>, solid: &Solid, relative_accuracy: f64) -> PyResult<f64> {
    py.detach(|| solid.body.volume(relative_accuracy))
        .map_err(|error| kernel_error("volume", error))
}

#[pyfunction]
fn _translate(py: Python<'_>, solid: &Solid, offset: [f64; 3]) -> PyResult<Solid> {
    py.detach(|| {
        let matrix = affine::translation(offset)?;
        let body = solid.body.copy()?;
        body.transform(&matrix)?;
        Ok(Solid { body })
    })
    .map_err(|error| kernel_error("translate", error))
}

#[pyfunction]
fn _bounds(py: Python<'_>, solid: &Solid) -> PyResult<([f64; 3], [f64; 3])> {
    py.detach(|| solid.body.bounds())
        .map_err(|error| kernel_error("bounds", error))
}

#[pyfunction]
fn _step_text(py: Python<'_>, solid: &Solid, file_name: &str, name: &str) -> PyResult<String> {
    py.detach(|| {
        let header = Header {
            file_name: file_name.to_owned(),
            originating_system: "solidfunc".to_owned(),
            preprocessor_version: format!("solidfunc {}", env!("CARGO_PKG_VERSION")),
            ..Header::default()
        };
        solidcore_bodies(&[(name, &solid.body)], &header)
    })
    .map_err(|error| SolidCoreError::new_err(format!("export_step: {error}")))
}

#[pymodule]
fn _core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Solid>()?;
    module.add("SolidCoreError", module.py().get_type::<SolidCoreError>())?;
    module.add_function(wrap_pyfunction!(_box, module)?)?;
    module.add_function(wrap_pyfunction!(_cylinder, module)?)?;
    module.add_function(wrap_pyfunction!(_union, module)?)?;
    module.add_function(wrap_pyfunction!(_intersection, module)?)?;
    module.add_function(wrap_pyfunction!(_difference, module)?)?;
    module.add_function(wrap_pyfunction!(_volume, module)?)?;
    module.add_function(wrap_pyfunction!(_translate, module)?)?;
    module.add_function(wrap_pyfunction!(_bounds, module)?)?;
    module.add_function(wrap_pyfunction!(_step_text, module)?)?;
    Ok(())
}
