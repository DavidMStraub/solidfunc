"""Build the clutch brick from CAD as Code, chapter 2, using solidfunc.

The studs are placed on the body's top face rather than at a height
computed by hand, so they follow the face when the body changes.
"""

import solidfunc as sf


def clutch_brick(
    *,
    length: float = 15.6,
    width: float = 7.8,
    height: float = 9.6,
    stud_diameter: float = 4.8,
    stud_height: float = 1.7,
    stud_spacing: float = 8.0,
) -> sf.Shape:
    """Return a brick body with two studs on its top face, in millimetres."""
    body = sf.box(size_x=length, size_y=width, size_z=height)
    top = sf.Plane.from_face(max(sf.faces(body), key=lambda face: face.centroid[2]))
    stud = sf.cylinder(diameter=stud_diameter, height=stud_height)
    studs = [
        sf.place(stud, top.offset(x=x)) for x in (-stud_spacing / 2, stud_spacing / 2)
    ]
    return sf.union(body, *studs)


if __name__ == "__main__":
    print(f"Clutch brick volume: {sf.volume(clutch_brick()):.3f} mm³")
