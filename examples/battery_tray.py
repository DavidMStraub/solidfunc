"""Build the battery tray from CAD as Code, chapter 4, using solidfunc.

A plate with a row of cell pockets and mirrored mounting holes. The lead-in
round is selected by radius and height, so it cannot catch the mounting
holes' rims.
"""

import solidfunc as sf


def battery_tray(
    *,
    width: float = 100.0,
    depth: float = 30.0,
    thickness: float = 6.0,
    cell_diameter: float = 18.0,
    clearance: float = 0.3,
    pocket_depth: float = 3.0,
    pitch: float = 24.0,
    cells: int = 3,
    hole_diameter: float = 3.4,
    lead_in: float = 1.0,
) -> sf.Shape:
    """Return a tray for a row of cylindrical cells, in millimetres."""
    plate = sf.box(size_x=width, size_y=depth, size_z=thickness)
    pocket_radius = cell_diameter / 2 + clearance
    pocket = sf.translate(
        sf.cylinder(radius=pocket_radius, height=pocket_depth + 1),
        z=thickness - pocket_depth,
    )
    pockets = [
        sf.translate(pocket, x=(i - (cells - 1) / 2) * pitch) for i in range(cells)
    ]
    hole = sf.translate(
        sf.cylinder(diameter=hole_diameter, height=thickness + 2),
        x=width / 2 - 6,
        y=depth / 2 - 3,
        z=-1,
    )
    holes = [hole, sf.mirror(hole, normal=(1, 0, 0))]
    tray = plate - sf.union(*pockets, *holes)

    rims = [
        edge
        for edge in sf.edges(tray)
        if edge.circle_radius is not None
        and abs(edge.circle_radius - pocket_radius) < 1e-6
        and edge.circle_center is not None
        and abs(edge.circle_center[2] - thickness) < 1e-6
    ]
    return sf.fillet(tray, rims, radius=lead_in)


if __name__ == "__main__":
    print(f"Battery tray volume: {sf.volume(battery_tray()):.3f} mm³")
