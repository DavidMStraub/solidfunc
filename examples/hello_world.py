"""Create and measure a real SolidCore solid through Python."""

import solidfunc as sf

block = sf.box(length=10, width=20, height=30)
moved = sf.translate(block, x=100)

print(f"Hello, SolidCore! Box volume: {sf.volume(block):.1f} mm³")
print(f"Original bounds: {sf.bounds(block)}")
print(f"Translated bounds: {sf.bounds(moved)}")

sf.export_step(block, "hello.step", name="Hello, SolidCore!")
print("Wrote hello.step; open it in a STEP viewer or import it with CadQuery.")
