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
    """Return a centred plate with a bearing hole and four counterbored holes.

    All dimensions are in millimetres. ``padding`` is the total reduction in
    length and width of the hole pattern, so hole centres are padding / 2
    from the edges. Counterbores open on the +Z face.
    """
    block = sf.box(
        length=length,
        width=width,
        height=thickness,
        origin=(-length / 2, -width / 2, -thickness / 2),
    )
    # Extend through-cut tools beyond both faces of the plate.
    overcut = 1.0
    cutters = sf.cylinder(
        radius=bearing_diameter / 2,
        height=thickness + 2 * overcut,
        origin=(0, 0, -thickness / 2 - overcut),
    )
    for x in (-(length - padding) / 2, (length - padding) / 2):
        for y in (-(width - padding) / 2, (width - padding) / 2):
            clearance = sf.cylinder(
                radius=clearance_diameter / 2,
                height=thickness + 2 * overcut,
                origin=(x, y, -thickness / 2 - overcut),
            )
            counterbore = sf.cylinder(
                radius=counterbore_diameter / 2,
                height=counterbore_depth + overcut,
                origin=(x, y, thickness / 2 - counterbore_depth),
            )
            cutters = cutters + clearance + counterbore

    result = block - cutters
    if result is None:
        raise ValueError("Parameters leave no material in the pillow block")
    return result


if __name__ == "__main__":
    part = bearing_pillow_block()
    destination = Path(__file__).resolve().parents[1] / "pillow_block.step"
    sf.export_step(part, destination, name="Bearing pillow block")
    print(f"Wrote {destination.name}; volume: {sf.volume(part):.3f} mm³")
