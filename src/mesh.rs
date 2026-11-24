//! Display tessellation and export meshing of SolidCore bodies.

use pyo3::prelude::*;
use solidcore_tess::{mesh, plan, MeshSpec, MeshTolerance, MESH_MIN_ANGLE};

use crate::{kernel_error, KernelError, Shape};

type Point = (f64, f64, f64);
type MeshData = (
    Vec<Point>,
    Vec<Point>,
    Vec<(u32, u32, u32)>,
    Vec<Vec<Point>>,
);
type ExportMeshData = (Vec<Point>, Vec<(u32, u32, u32)>);

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

/// Mesh a body for export: the kernel's mesh path, with the faces joined at their shared
/// vertices. Returns the vertex positions and counter-clockwise triangles as seen from outside.
#[pyfunction]
fn _mesh(
    py: Python<'_>,
    shape: &Shape,
    chord_tolerance: Option<f64>,
    max_edge_length: Option<f64>,
) -> PyResult<ExportMeshData> {
    py.detach(|| {
        let (lower, upper) = shape.body.bounds().map_err(|e| kernel_error("mesh", e))?;
        let [dx, dy, dz] = std::array::from_fn(|i| upper[i] - lower[i]);
        let size = dx.hypot(dy).hypot(dz);
        let chord = chord_tolerance.unwrap_or_else(|| MeshTolerance::export_of(size).chord);
        let spec = MeshSpec {
            chord,
            size: max_edge_length,
            min_angle: MESH_MIN_ANGLE,
        };
        let (record, _) = shape
            .body
            .to_record()
            .map_err(|e| kernel_error("mesh", e))?;
        let (plan, stats) = mesh(&record, &spec, size, None)
            .map_err(|e| KernelError::new_err(format!("mesh: {e}")))?;
        // `mesh` already fails for a face it cannot mesh; check again so that a face left out
        // can never give an open mesh. Faces short of their shape or of the chord tolerance
        // (`unshaped`, `over_tolerance`, `edges_capped`) are meshed and do not fail.
        if let Some(face) = stats.unmeshed.first() {
            return Err(KernelError::new_err(format!(
                "mesh: could not mesh face {}: {}",
                face.face, face.reason
            )));
        }
        let (welded, refused) = plan
            .welded()
            .map_err(|e| KernelError::new_err(format!("mesh: {e}")))?;
        if let Some(face) = refused.first() {
            return Err(KernelError::new_err(format!(
                "mesh: could not mesh face {}: {}",
                face.face, face.reason
            )));
        }
        Ok((
            welded
                .positions
                .into_iter()
                .map(|p| (p.x, p.y, p.z))
                .collect(),
            welded
                .triangles
                .into_iter()
                .map(|[a, b, c]| (a, b, c))
                .collect(),
        ))
    })
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(_tessellate, module)?)?;
    module.add_function(wrap_pyfunction!(_mesh, module)?)
}
