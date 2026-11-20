"""Render the README gallery images into docs/gallery with PyVista.

Install PyVista first (``pip install pyvista``), then run this script from
the repository root.
"""

import sys
from collections.abc import Callable
from pathlib import Path

import solidfunc as sf
from solidfunc.view import show

EXAMPLES = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLES))

from battery_tray import battery_tray  # noqa: E402
from clutch_brick import clutch_brick  # noqa: E402
from duct import duct  # noqa: E402
from swept_elbow import swept_elbow  # noqa: E402

PARTS: dict[str, Callable[[], sf.Shape]] = {
    "clutch-brick": clutch_brick,
    "battery-tray": battery_tray,
    "swept-elbow": swept_elbow,
    "duct": duct,
}

if __name__ == "__main__":
    destination = EXAMPLES.parent / "docs" / "gallery"
    destination.mkdir(parents=True, exist_ok=True)
    for name, build in PARTS.items():
        # A fine chord tolerance keeps spline faces free of visible facets.
        show(build(), chord_tolerance=0.02, screenshot=destination / f"{name}.png")
        print(f"Wrote docs/gallery/{name}.png")
