"""Build the hollow elbow from CAD as Code, chapter 7, using solidfunc.

A ring-shaped profile is swept along a polyline with two right-angle
corners; the bore stays open along the whole path.
"""

import solidfunc as sf


def swept_elbow(
    *, outer_radius: float = 12.0, wall: float = 4.0, leg: float = 30.0
) -> sf.Shape:
    """Return a hollow tube with two mitred corners, in millimetres."""
    section = sf.profile(
        sf.circle(radius=outer_radius), holes=[sf.circle(radius=outer_radius - wall)]
    )
    path = sf.polyline3d([(0, 0, 0), (leg, 0, 0), (leg, leg, 0), (2 * leg, leg, 0)])
    start = sf.Plane.from_normal(
        origin=path.point_at(0), normal=path.tangent_at(0), x_dir=(0, 0, 1)
    )
    return sf.sweep(section, path, plane=start)


if __name__ == "__main__":
    volume = sf.volume(swept_elbow(), relative_tolerance=1e-6)
    print(f"Swept elbow volume: {volume:.3f} mm³")
