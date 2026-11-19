//! STEP solid exchange through the kernel's record reader.

use std::collections::BTreeMap;

use pyo3::prelude::*;
use solidcore_ops::{boolean::union_all, placed_bodies, Body};
use solidcore_record::step::product;
use solidcore_step::{p21, topology};

use crate::{KernelError, Shape};

fn read(text: &str) -> Result<Body, String> {
    let exchange = p21::parse(text).map_err(|error| error.to_string())?;
    let read = topology::read_solids(&exchange);
    if let Some(failure) = read.failures.first() {
        return Err(format!(
            "STEP entity #{}: {}",
            failure.item, failure.message
        ));
    }
    if read.solids.is_empty() || read.solids.iter().any(|solid| solid.sheet) {
        return Err("expected closed STEP solids".to_owned());
    }

    let structure = product::read(&exchange).map_err(|error| error.to_string())?;
    let placements = placed_bodies(&structure)?;
    let records: BTreeMap<_, _> = read
        .solids
        .into_iter()
        .map(|solid| (solid.item, solid.brep))
        .collect();
    let from_record = |record| {
        Body::from_record(record, false)
            .map(|(body, _)| body)
            .map_err(|error| error.to_string())
    };
    let bodies: Vec<_> = if placements.is_empty() {
        if !structure.occurrences.is_empty() {
            return Err("could not resolve STEP assembly placements".to_owned());
        }
        records
            .values()
            .map(from_record)
            .collect::<Result<_, _>>()?
    } else {
        placements
            .into_iter()
            .map(|placed| {
                let record = records
                    .get(&placed.entity)
                    .ok_or_else(|| format!("unsupported STEP body #{}", placed.entity))?;
                let body = from_record(record)?;
                body.transform(&placed.transform)
                    .map_err(|error| error.to_string())?;
                Ok(body)
            })
            .collect::<Result<_, String>>()?
    };
    union_all(bodies).map_err(|error| error.to_string())
}

#[pyfunction]
fn _import_step(py: Python<'_>, text: &str) -> PyResult<Shape> {
    py.detach(|| read(text))
        .map(|body| Shape { body })
        .map_err(|error| KernelError::new_err(format!("import_step: {error}")))
}

pub(super) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(_import_step, module)?)
}
