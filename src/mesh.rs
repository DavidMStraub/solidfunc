//! Display tessellation of SolidCore bodies.

use pyo3::prelude::*;
use solidcore_tess::{plan, MeshTolerance};

use crate::{kernel_error, KernelError, Shape};

type Point = (f64, f64, f64);
type MeshData = (
    Vec<Point>,
    Vec<Point>,
    Vec<(u32, u32, u32)>,
    Vec<Vec<Point>>,
);

#[pyfunction]
fn _tessellate(py: Python<'_>, shape: &Shape, chord_tolerance: Option<f64>) -> PyResult<MeshData> {
    py.detach(|| {
        let (lower, upper) = shape
            .body
            .bounds()
            .map_err(|e| kernel_error("tessellate", e))?;
        let [dx, dy, dz] = std::array::from_fn(|i| upper[i] - lower[i]);
        let size = dx.hypot(dy).hypot(dz);
        let tolerance =
            chord_tolerance.map_or_else(|| MeshTolerance::display_of(size), MeshTolerance::display);
        let (record, _) = shape
            .body
            .to_record()
            .map_err(|e| kernel_error("tessellate", e))?;
        let (plan, stats) = plan(&record, &tolerance, size)
            .map_err(|e| KernelError::new_err(format!("tessellate: {e}")))?;
        let (mesh, refused) = plan.evaluate();
        if let Some(face) = stats.unmeshed.first().or_else(|| refused.first()) {
            return Err(KernelError::new_err(format!(
                "tessellate: could not mesh face {}: {}",
                face.face, face.reason
            )));
        }
        let edges = mesh
            .edges
            .iter()
            .enumerate()
            .filter(|(index, points)| points.len() >= 2 && mesh.shaded_edge_visible(*index))
            .map(|(_, points)| points.iter().map(|p| (p.x, p.y, p.z)).collect())
            .collect();
        Ok((
            mesh.positions
                .into_iter()
                .map(|p| (p.x, p.y, p.z))
                .collect(),
            mesh.normals.into_iter().map(|p| (p.x, p.y, p.z)).collect(),
            mesh.triangles
                .into_iter()
                .map(|[a, b, c]| (a, b, c))
                .collect(),
            edges,
        ))
    })
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(_tessellate, module)?)
}
