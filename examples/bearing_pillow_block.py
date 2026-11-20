"""Build the bearing pillow block from CadQuery's examples using solidfunc.

Reference: https://cadquery.readthedocs.io/en/latest/examples.html
Section: A Parametric Bearing Pillow Block.
"""

from pathlib import Path

import solidfunc as sf


def bearing_pillow_block(
    *,
    length: float = 30.0,
    width: float = 40.0,
    thickness: float = 10.0,
    bearing_diameter: float = 22.0,
    padding: float = 8.0,
    clearance_diameter: float = 2.4,
    counterbore_diameter: float = 4.4,
    counterbore_depth: float = 2.1,
) -> sf.Shape:
    """Return a plate with a bearing hole and four counterbored holes.

    All dimensions are in millimetres. The plate is centred in XY with its
    base at z = 0. ``padding`` is the total reduction in length and width of
    the hole pattern, so hole centres are padding / 2 from the edges.
    Counterbores open on the top face.
    """
    block = sf.box(size_x=length, size_y=width, size_z=thickness)
    # Extend through-cut tools beyond both faces of the plate.
    overcut = 1.0
    through = thickness + 2 * overcut
    cutters = sf.translate(
        sf.cylinder(radius=bearing_diameter / 2, height=through), z=-overcut
    )
    clearance = sf.cylinder(radius=clearance_diameter / 2, height=through)
    counterbore = sf.cylinder(
        radius=counterbore_diameter / 2, height=counterbore_depth + overcut
    )
    for x in (-(length - padding) / 2, (length - padding) / 2):
        for y in (-(width - padding) / 2, (width - padding) / 2):
            cutters = cutters + sf.translate(clearance, x=x, y=y, z=-overcut)
            cutters = cutters + sf.translate(
                counterbore, x=x, y=y, z=thickness - counterbore_depth
            )

    result = block - cutters
    if result is None:
        raise ValueError("Parameters leave no material in the pillow block")
    return result


if __name__ == "__main__":
    part = bearing_pillow_block()
    destination = Path(__file__).resolve().parents[1] / "pillow_block.step"
    sf.export_step(part, destination, name="Bearing pillow block")
    print(f"Wrote {destination.name}; volume: {sf.volume(part):.3f} mm³")
