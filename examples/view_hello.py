"""Display the hello-world STEP export in OCP CAD Viewer."""

from pathlib import Path

import cadquery as cq
from ocp_vscode import show

step_path = Path(__file__).resolve().parents[1] / "hello.step"
part = cq.importers.importStep(str(step_path))
show(part)
