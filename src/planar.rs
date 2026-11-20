//! Bindings for XY curves, connected paths and filled profiles.

use std::f64::consts::TAU;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use solidcore_ops::prism::{
    extrude_planar_regions, loop_placement, region_area, LoopPlacement, EXTRUDE_TOLERANCE,
};
use solidcore_record::{Loop2, Region2, Seg2, Vec2};

use crate::{kernel_error, repr_count, repr_number, repr_point, Shape};

/// A directed XY curve. Its start and end are (x, y) coordinates in mm.
#[pyclass(frozen, module = "solidfunc.planar")]
#[derive(Clone)]
struct Curve2D {
    segment: Seg2,
    #[pyo3(get)]
    start: (f64, f64),
    #[pyo3(get)]
    end: (f64, f64),
}

#[pymethods]
impl Curve2D {
    fn __repr__(&self) -> String {
        let kind = match self.segment {
            Seg2::Line { .. } => "line".to_string(),
            Seg2::Arc { radius, .. } => format!("arc r={}", repr_number(radius)),
            Seg2::Cubic { .. } | Seg2::Bezier { .. } => "spline".to_string(),
            Seg2::Conic { .. } => "conic".to_string(),
        };
        format!(
            "<Curve2D {kind}, {} to {}>",
            repr_point(&[self.start.0, self.start.1]),
            repr_point(&[self.end.0, self.end.1])
        )
    }
}

/// An ordered chain of connected XY curves.
#[pyclass(frozen, module = "solidfunc.planar")]
pub(super) struct Path2D {
    curves: Vec<Curve2D>,
    #[pyo3(get)]
    is_closed: bool,
}

#[pymethods]
impl Path2D {
    fn __repr__(&self) -> String {
        let state = if self.is_closed { "closed" } else { "open" };
        format!(
            "<Path2D {state}, {}>",
            repr_count(self.curves.len(), "curve")
        )
    }

    /// Get the curves in traversal order.
    #[getter]
    fn curves<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, self.curves.iter().cloned())
    }
}

impl Path2D {
    pub(super) fn as_loop(&self) -> PyResult<Loop2> {
        if !self.is_closed {
            return Err(PyValueError::new_err(
                "profile boundaries must be closed paths",
            ));
        }
        Ok(Loop2 {
            segs: self.curves.iter().map(|curve| curve.segment).collect(),
        })
    }
}

/// An opaque filled region in the XY plane, optionally with holes.
#[pyclass(frozen, module = "solidfunc")]
pub(super) struct Profile {
    pub(super) region: Region2,
}

#[pymethods]
impl Profile {
    fn __repr__(&self) -> String {
        match self.region.holes.len() {
            0 => "<Profile>".into(),
            holes => format!("<Profile with {}>", repr_count(holes, "hole")),
        }
    }
}

fn same_point(a: (f64, f64), b: (f64, f64)) -> bool {
    (a.0 - b.0).hypot(a.1 - b.1) <= EXTRUDE_TOLERANCE
}

#[pyfunction]
fn _line(start: (f64, f64), end: (f64, f64)) -> PyResult<Curve2D> {
    if [start.0, start.1, end.0, end.1]
        .iter()
        .any(|x| !x.is_finite())
        || start == end
    {
        return Err(PyValueError::new_err(
            "line needs distinct, finite endpoints",
        ));
    }
    Ok(Curve2D {
        segment: Seg2::Line {
            a: Vec2::new(start.0, start.1),
            b: Vec2::new(end.0, end.1),
        },
        start,
        end,
    })
}

#[pyfunction]
fn _arc(center: [f64; 2], radius: f64, start: f64, sweep: f64) -> PyResult<Curve2D> {
    if !(center.iter().all(|x| x.is_finite())
        && radius.is_finite()
        && radius > 0.0
        && start.is_finite()
        && sweep.abs() > 0.0
        && sweep.abs() <= TAU)
    {
        return Err(PyValueError::new_err("arc needs a finite center and angles, a positive finite radius, and a nonzero sweep of at most one turn"));
    }
    let start = start.rem_euclid(TAU);
    let [x, y] = center;
    let point = |angle: f64| (x + radius * angle.cos(), y + radius * angle.sin());
    let first = point(start);
    let last = if sweep.abs() == TAU {
        first
    } else {
        point(start + sweep)
    };
    if [first.0, first.1, last.0, last.1]
        .iter()
        .any(|x| !x.is_finite())
    {
        return Err(PyValueError::new_err("arc endpoints must be finite"));
    }
    Ok(Curve2D {
        segment: Seg2::Arc {
            center: Vec2::from(center),
            radius,
            start,
            sweep,
        },
        start: first,
        end: last,
    })
}

#[pyfunction]
fn _path(curves: Vec<PyRef<'_, Curve2D>>) -> PyResult<Path2D> {
    let (Some(first), Some(last)) = (curves.first(), curves.last()) else {
        return Err(PyValueError::new_err("path needs at least one curve"));
    };
    if curves
        .windows(2)
        .any(|pair| !same_point(pair[0].end, pair[1].start))
    {
        return Err(PyValueError::new_err(
            "path curves must connect end to start in order",
        ));
    }
    Ok(Path2D {
        is_closed: same_point(last.end, first.start),
        curves: curves.iter().map(|curve| (**curve).clone()).collect(),
    })
}

fn checked_profile(operation: &str, region: Region2) -> PyResult<Profile> {
    let area = region_area(&region).map_err(|error| kernel_error(operation, error))?;
    if area.sign().is_none() {
        return Err(PyValueError::new_err(format!(
            "{operation} requires a nonzero signed area"
        )));
    }
    Ok(Profile { region })
}

#[pyfunction]
fn _profile(outer: &Path2D, holes: Vec<PyRef<'_, Path2D>>) -> PyResult<Profile> {
    let outer = outer.as_loop()?;
    let mut loops = Vec::with_capacity(holes.len());
    let placement = |a: &Loop2, b: &Loop2| loop_placement(a, b, EXTRUDE_TOLERANCE);
    for hole in holes {
        let hole = hole.as_loop()?;
        if placement(&hole, &outer) != Some(LoopPlacement::Inside) {
            return Err(PyValueError::new_err(
                "profile holes must lie strictly inside the outer boundary",
            ));
        }
        if loops.iter().any(|other| {
            placement(&hole, other) != Some(LoopPlacement::Outside)
                || placement(other, &hole) != Some(LoopPlacement::Outside)
        }) {
            return Err(PyValueError::new_err("profile holes must be disjoint"));
        }
        loops.push(hole);
    }

    // The kernel normalizes winding for extrusion. Check the area of each boundary
    // separately so the caller can supply any winding.
    for hole in &loops {
        checked_profile(
            "profile hole",
            Region2 {
                outer: hole.clone(),
                holes: Vec::new(),
            },
        )?;
    }
    checked_profile(
        "profile",
        Region2 {
            outer,
            holes: Vec::new(),
        },
    )
    .map(|mut profile| {
        profile.region.holes = loops;
        profile
    })
}
#[pyfunction]
fn _extrude(
    py: Python<'_>,
    profile: &Profile,
    distance: f64,
    plane: crate::modeling::Frame,
) -> PyResult<Shape> {
    if !distance.is_finite() || distance == 0.0 {
        return Err(PyValueError::new_err("distance must be finite and nonzero"));
    }
    py.detach(|| {
        extrude_planar_regions(
            &crate::modeling::plane(plane),
            std::slice::from_ref(&profile.region),
            distance.min(0.0),
            distance.max(0.0),
        )
    })
    .map(|body| Shape { body })
    .map_err(|error| kernel_error("extrude", error))
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Curve2D>()?;
    module.add_class::<Path2D>()?;
    module.add_class::<Profile>()?;
    module.add_function(wrap_pyfunction!(_line, module)?)?;
    module.add_function(wrap_pyfunction!(_arc, module)?)?;
    module.add_function(wrap_pyfunction!(_path, module)?)?;
    module.add_function(wrap_pyfunction!(_profile, module)?)?;
    module.add_function(wrap_pyfunction!(_extrude, module)?)?;
    Ok(())
}
