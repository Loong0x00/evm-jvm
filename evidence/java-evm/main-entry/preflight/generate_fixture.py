#!/usr/bin/env python3
"""Deterministically compile generated Java8 fixture and make its opaque ZIP.
Oracle.java is deliberately compiled separately and never enters the ZIP.
"""
import hashlib, json, pathlib, subprocess, sys, zipfile

root = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else root / "fixture-output"
if out.exists():
    raise SystemExit("refusing existing output: " + str(out))
out.mkdir(parents=True)
javac = pathlib.Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = pathlib.Path("/usr/lib/jvm/java-8-openjdk/bin/java")
for tool in (javac, java):
    if not tool.is_file(): raise SystemExit("missing pinned Java 8 tool: " + str(tool))
classes = out / "classes"; classes.mkdir()
subprocess.run([str(javac), "-source", "8", "-target", "8", "-g:none", "-d", str(classes), str(root/"Launcher.java"), str(root/"TargetMain.java")], check=True)
oracle = out / "oracle"; oracle.mkdir()
subprocess.run([str(javac), "-source", "8", "-target", "8", "-g:none", "-cp", str(classes), "-d", str(oracle), str(root/"Oracle.java")], check=True)
oracle_out = "".join(subprocess.check_output([str(java), "-cp", str(classes)+":"+str(oracle), "Oracle", str(mode)], text=True) for mode in range(4))
expected = "0:R:341\n1:R:381\n2:R:351\n3:X:java.lang.NullPointerException\n"
if oracle_out != expected: raise SystemExit("oracle mismatch: " + repr(oracle_out))
zip_path = out / "main-entry-generated.zip"
with zipfile.ZipFile(str(zip_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in ("Launcher.class", "TargetMain.class"):
        info = zipfile.ZipInfo(name, (1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644 << 16
        z.writestr(info, (classes/name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
metadata = out / "fixture.json"
metadata.write_text(json.dumps({
    "javac": subprocess.check_output([str(javac), "-version"], stderr=subprocess.STDOUT, text=True).strip(),
    "java": subprocess.check_output([str(java), "-version"], stderr=subprocess.STDOUT, text=True).splitlines()[0],
    "oracle": oracle_out,
    "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [classes/"Launcher.class", classes/"TargetMain.class", zip_path]},
}, indent=2, sort_keys=True) + "\n")
print(zip_path)
