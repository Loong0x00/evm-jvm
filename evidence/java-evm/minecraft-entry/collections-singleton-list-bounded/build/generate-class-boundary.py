#!/usr/bin/env python3
"""Generate 149 harmless Java8 raw classes plus the completed singleton probe."""
import pathlib, zipfile
D = pathlib.Path(__file__).resolve().parents[1]
src = D / "build/class-boundary/src"
out = D / "build/class-boundary/classes"
src.mkdir(parents=True, exist_ok=True)
out.mkdir(parents=True, exist_ok=True)
for i in range(149):
    (src / f"Boundary{i:03}.java").write_text(f"public final class Boundary{i:03} {{ }}\n")
files = [D / "build/fixture/SingletonListProbe.class"] + [out / f"Boundary{i:03}.class" for i in range(149)]
assert all(p.is_file() for p in files), "compile fixture and Boundary sources first"
with zipfile.ZipFile(D / "build/class-boundary.zip", "w", zipfile.ZIP_STORED) as z:
    for p in files:
        z.write(p, p.name)
(D / "build/class-boundary.bindings").write_text(",".join(p.name for p in files) + "\n")
