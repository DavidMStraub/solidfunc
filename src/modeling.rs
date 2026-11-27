//! Solid construction from placed sections and spatial paths.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use solidcore::eval::{Curve as EvalGeometry, CurveEval};
use solidcore::kernel::Kernel;
use solidcore::prism::profile::curve_on_frame;
use solidcore::sweep::cornered::cornered_sweep;
use solidcore::sweep::stations::{Laws, Path, Piece};
use solidcore::Vec3;
use solidcore_ops::sweep::{self, Curve, LoftSection, SweepFrame};
use solidcore_ops::{boolean::boolean, curve_fit, Body, BooleanOp, Error, Result};
use solidcore_record::{brep::Curve as RecordCurve, Plane, Seg2};

use crate::planar::Profile;
use crate::{kernel_error, repr_count, KernelError, Shape};

pub(super) type Frame = ([f64; 3], [f64; 3], [f64; 3]);

pub(super) fn plane((origin, x, y): Frame) -> Plane {
    Plane {
        origin: origin.into(),
        x: x.into(),
        y: y.into(),
    }
}

fn placed(segments: &[Seg2], plane: &Plane) -> Result<Vec<Curve>> {
    segments
        .iter()
        .map(|segment| {
            // `arc()` already refuses the zero-sweep arcs the kernel cannot place.
            Curve::from_seg2(segment, plane).ok_or(Error::Refused {
                operation: "profile placement",
                reason: "a profile segment cannot be placed; this is a solidfunc bug",
            })
        })
        .collect()
}

fn outer(profile: &Profile) -> PyResult<&[Seg2]> {
    if !profile.region.holes.is_empty() {
        return Err(PyValueError::new_err(
            "revolve and loft require a profile without holes",
        ));
    }
    Ok(&profile.region.outer.segs)
}

/// A connected spatial path. Construct it with polyline3d or spline3d.
#[pyclass(frozen, module = "solidfunc")]
struct Path3D {
    curves: Vec<Curve>,
    evaluator: CurveEval,
    #[pyo3(get)]
    is_closed: bool,
}

impl Path3D {
    fn new(points: &[[f64; 3]], curves: Vec<Curve>, geometry: EvalGeometry) -> PyResult<Self> {
        let evaluator = CurveEval::new(&geometry)
            .map_err(|error| KernelError::new_err(format!("path evaluation: {error}")))?;
        let (Some(first), Some(last)) = (points.first(), points.last()) else {
            return Err(PyValueError::new_err("path needs points"));
        };
        let [x, y, z] = std::array::from_fn(|i| first[i] - last[i]);
        Ok(Self {
            curves,
            evaluator,
            is_closed: x.hypot(y).hypot(z) <= solidcore_ops::prism::EXTRUDE_TOLERANCE,
        })
    }

    fn parameter(&self, fraction: f64) -> PyResult<f64> {
        if !(0.0..=1.0).contains(&fraction) {
            return Err(PyValueError::new_err(
                "path parameter must be between 0 and 1",
            ));
        }
        Ok(fraction * self.curves.len() as f64)
    }
}

#[pymethods]
impl Path3D {
    fn __repr__(&self) -> String {
        let state = if self.is_closed { "closed" } else { "open" };
        format!(
            "<Path3D {state}, {}>",
            repr_count(self.curves.len(), "curve")
        )
    }

    /// Return the world XYZ point at a parameter from 0 to 1.
    ///
    /// Each polyline segment takes an equal share of the range. A spline
    /// uses its normalized knot parameter. The parameter is dimensionless.
    fn point_at(&self, parameter: f64) -> PyResult<(f64, f64, f64)> {
        self.evaluator
            .point(self.parameter(parameter)?)
            .map(|point| (point.x, point.y, point.z))
            .ok_or_else(|| KernelError::new_err("could not evaluate path point"))
    }

    /// Return the unit XYZ tangent at a parameter from 0 to 1.
    ///
    /// At a polyline corner, use the outgoing segment, and at the final
    /// endpoint use the incoming segment.
    fn tangent_at(&self, parameter: f64) -> PyResult<(f64, f64, f64)> {
        let (_, derivative) = self
            .evaluator
            .derivs(self.parameter(parameter)?)
            .ok_or_else(|| KernelError::new_err("could not evaluate path tangent"))?;
        let tangent = derivative
            .unitize()
            .map_err(|_| KernelError::new_err("path tangent is undefined"))?;
        Ok((tangent.x, tangent.y, tangent.z))
    }
}

#[pyfunction]
fn _polyline3d(points: Vec<[f64; 3]>) -> PyResult<Path3D> {
    if points.len() < 2 || points.iter().flatten().any(|x| !x.is_finite()) {
        return Err(PyValueError::new_err(
            "polyline3d needs at least two finite points",
        ));
    }
    if points.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err(PyValueError::new_err(
            "polyline3d has consecutive duplicate points",
        ));
    }
    let curves = points
        .windows(2)
        .map(|pair| Curve::Line {
            start: pair[0],
            end: pair[1],
        })
        .collect();
    Path3D::new(
        &points,
        curves,
        EvalGeometry::Polyline {
            points: points.clone(),
        },
    )
}

#[pyfunction]
fn _spline(py: Python<'_>, points: Vec<[f64; 3]>, degree: usize) -> PyResult<Path3D> {
    let (curve, _) = py
        .detach(|| curve_fit::ep_curve(&points, degree))
        .map_err(|error| kernel_error("spline", error))?;
    let RecordCurve::Spline {
        knots,
        points: control_points,
    } = curve
    else {
        return Err(KernelError::new_err(
            "spline: kernel returned an unexpected curve",
        ));
    };
    let curve = Curve::Nurbs {
        degree,
        points: control_points
            .iter()
            .map(|&[x, y, z]| [x, y, z, 1.0])
            .collect(),
        knots: knots.clone(),
    };
    Path3D::new(
        &points,
        vec![curve],
        EvalGeometry::Spline {
            knots,
            points: control_points,
        },
    )
}

#[pyfunction]
fn _revolve(
    py: Python<'_>,
    profile: &Profile,
    frame: Frame,
    origin: [f64; 3],
    axis: [f64; 3],
    angle: f64,
) -> PyResult<Shape> {
    let segments = outer(profile)?;
    py.detach(|| {
        let curves = placed(segments, &plane(frame))?;
        sweep::revolve(&curves, origin, axis, angle, true)
    })
    .map(|body| Shape { body })
    .map_err(|error| kernel_error("revolve", error))
}

#[pyfunction]
fn _loft(
    py: Python<'_>,
    sections: Vec<(PyRef<'_, Profile>, Frame)>,
    degree: u32,
) -> PyResult<Shape> {
    let sections: Vec<_> = sections
        .iter()
        .map(|(profile, frame)| {
            Ok(LoftSection {
                plane: plane(*frame),
                segs: outer(profile)?.to_vec(),
            })
        })
        .collect::<PyResult<_>>()?;
    if sections.len() < 2 || !(1..=3).contains(&degree) || degree as usize >= sections.len() {
        return Err(PyValueError::new_err(
            "loft needs more sections than its degree (1 to 3)",
        ));
    }
    py.detach(|| {
        let matching = sweep::match_loft_sections(&sections, 512)?.ok_or(Error::Unsupported(
            "loft sections exceed the matching limit",
        ))?;
        let curves: Vec<_> = matching
            .iter()
            .zip(&sections)
            .map(|(matched, section)| placed(&matched.segs, &section.plane))
            .collect::<Result<_>>()?;
        sweep::loft(&curves, degree, true)
    })
    .map(|body| Shape { body })
    .map_err(|error| kernel_error("loft", error))
}

#[pyfunction]
fn _loft_paths(py: Python<'_>, paths: Vec<PyRef<'_, Path3D>>, degree: u32) -> PyResult<Shape> {
    if paths.len() < 2 || !(1..=3).contains(&degree) || degree as usize >= paths.len() {
        return Err(PyValueError::new_err(
            "loft needs more sections than its degree (1 to 3)",
        ));
    }
    let count = paths[0].curves.len();
    if paths
        .iter()
        .any(|path| !path.is_closed || path.curves.len() != count)
    {
        return Err(PyValueError::new_err(
            "spatial loft sections must be closed paths with corresponding curves",
        ));
    }
    let sections: Vec<_> = paths.iter().map(|path| path.curves.clone()).collect();
    py.detach(|| sweep::loft(&sections, degree, true))
        .map(|body| Shape { body })
        .map_err(|error| kernel_error("loft", error))
}

fn mitred_sweep(segments: &[Seg2], plane: &Plane, curves: &[Curve]) -> Result<Option<Body>> {
    if curves.len() < 2 {
        return Ok(None);
    }
    let vec = |[x, y, z]: [f64; 3]| Vec3::new(x, y, z);
    let Some(pieces) = curves
        .iter()
        .map(|curve| match *curve {
            Curve::Line { start, end } => Some(Piece::Line {
                a: vec(start),
                b: vec(end),
            }),
            _ => None,
        })
        .collect()
    else {
        return Ok(None);
    };
    let path = Path { pieces };
    let record_error = |error: solidcore::SolidError| Error::Record(error.to_string());
    if path.corner_fractions().map_err(record_error)?.is_empty() {
        return Ok(None);
    }

    let mut kernel = Kernel::default();
    let frame = solidcore_convert::plane(plane);
    let profile = segments
        .iter()
        .map(|segment| curve_on_frame(&kernel, &frame, 0.0, &solidcore_convert::seg2(segment)))
        .collect::<solidcore::Result<Vec<_>>>()
        .map_err(record_error)?;
    let normal = vec(frame.x_axis).cross(vec(frame.y_axis));
    let mut body = cornered_sweep(&mut kernel, &profile, normal, &path, &Laws::default())
        .map_err(record_error)?;
    let (record, _) = solidcore_convert::brep::to_record(&mut kernel, &mut body)
        .map_err(|error| Error::Record(error.to_string()))?;
    Body::from_record(&record, false).map(|(body, _)| Some(body))
}

fn sweep_boundary(segments: &[Seg2], plane: &Plane, path: &[Curve]) -> Result<Body> {
    if let Some(body) = mitred_sweep(segments, plane, path)? {
        return Ok(body);
    }
    let curves = placed(segments, plane)?;
    sweep::sweep_placed(&curves, path, SweepFrame::Follow, true).map(|(body, _, _)| body)
}

#[pyfunction]
fn _sweep(py: Python<'_>, profile: &Profile, frame: Frame, path: &Path3D) -> PyResult<Shape> {
    py.detach(|| {
        let plane = plane(frame);
        let mut body = sweep_boundary(&profile.region.outer.segs, &plane, &path.curves)?;
        // Sweep each opening along the same path and subtract it through both end caps.
        for hole in &profile.region.holes {
            let tool = sweep_boundary(&hole.segs, &plane, &path.curves)?;
            body = boolean(body, tool, BooleanOp::Subtract)?.ok_or(Error::Empty)?;
        }
        Ok(Shape { body })
    })
    .map_err(|error| kernel_error("sweep", error))
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Path3D>()?;
    module.add_function(wrap_pyfunction!(_polyline3d, module)?)?;
    module.add_function(wrap_pyfunction!(_spline, module)?)?;
    module.add_function(wrap_pyfunction!(_revolve, module)?)?;
    module.add_function(wrap_pyfunction!(_loft, module)?)?;
    module.add_function(wrap_pyfunction!(_loft_paths, module)?)?;
    module.add_function(wrap_pyfunction!(_sweep, module)?)?;
    Ok(())
}
