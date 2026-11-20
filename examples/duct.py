"""Build the round-to-rectangular duct from CAD as Code, chapter 7.

A loft runs from a circle at the base to a rectangle at the top. Both
sections are closed boundaries filled with profile().
"""

import solidfunc as sf


def duct(
    *,
    radius: float = 25.0,
    size_x: float = 60.0,
    size_y: float = 40.0,
    height: float = 80.0,
) -> sf.Shape:
    """Return a solid transition from a circle to a rectangle, in millimetres."""
    base = sf.profile(sf.circle(radius=radius))
    top = sf.profile(sf.rectangle(size_x=size_x, size_y=size_y))
    return sf.loft([(base, sf.Plane()), (top, sf.Plane(origin=(0, 0, height)))])


if __name__ == "__main__":
    print(f"Duct volume: {sf.volume(duct(), relative_tolerance=1e-6):.3f} mm³")
