#!/usr/bin/env python3
"""Generate only Java-8 count-boundary fixtures; no original input is read."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, zipfile

out = Path(sys.argv[1]).resolve()
assert not out.exists()
out.mkdir()
src = out / "src"
classes = out / "classes"
src.mkdir()
classes.mkdir()
javac = "/usr/lib/jvm/java-8-openjdk/bin/javac"
java = "/usr/lib/jvm/java-8-openjdk/bin/java"
assert Path(javac).is_file() and Path(java).is_file()

def source(count, pads=()):
    tails = count - 1
    calls = " + ".join("Tail%02d.touch()" % i for i in range(1, tails + 1))
    fields = "".join("  private static final String PAD%02d = \"%s\";\n" % (i, x) for i, x in enumerate(pads))
    return """public final class CountMain {
%s  static int sentinel;
  public static void main(String[] ignored) {
    sentinel = %s;
    if (sentinel != %d) throw new Error();
  }
}
""" % (fields, calls, tails * (tails + 1) // 2)

def build(count, target=None):
    assert 1 <= count <= 31
    label = str(count) if target is None else "%d-%d" % (count, target)
    d = src / label
    d.mkdir()
    c = classes / label
    c.mkdir()
    for i in range(1, count):
        (d / ("Tail%02d.java" % i)).write_text("final class Tail%02d { static int touch() { return %d; } }\n" % (i, i))
    def compile(pads=()):
        (d / "CountMain.java").write_text(source(count, pads))
        shutil.rmtree(c, ignore_errors=True)
        c.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", str(c), *map(str, sorted(d.glob("*.java")))], check=True)
        return sum(p.stat().st_size for p in c.glob("*.class"))
    total = compile()
    pads = []
    if target is not None:
        assert total < target
        zero = compile([""] * 5)
        overhead = zero - total
        need = target - total - overhead
        assert 0 <= need <= 5 * 65000, (count, target, total, overhead, need)
        pads = [(chr(65 + i) + "x" * (min(65000, need - i * 65000) - 1)) if need > i * 65000 else "" for i in range(5)]
        total = compile(pads)
        for _ in range(3):
            delta = target - total
            if delta == 0:
                break
            at = max(i for i, value in enumerate(pads) if value)
            assert 0 <= len(pads[at]) + delta <= 65000
            pads[at] = pads[at][:len(pads[at]) + delta] if delta < 0 else pads[at] + "x" * delta
            total = compile(pads)
        assert total == target, (count, target, total)
    subprocess.run([java, "-cp", str(c), "CountMain"], check=True)
    entries = ["CountMain.class"] + ["Tail%02d.class" % i for i in range(1, count)]
    z = out / (str(count) + (".zip" if target is None else ("-%d.zip" % target)))
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (c / name).read_bytes())
    receipt = {
        "java8TESTOracle": True, "bindingCount": count, "entries": entries,
        "totalClassBytes": total, "zipSHA256": hashlib.sha256(z.read_bytes()).hexdigest(),
        "classSHA256": {name: hashlib.sha256((c / name).read_bytes()).hexdigest() for name in entries},
        "classBytes": {name: (c / name).stat().st_size for name in entries},
    }
    assert all(value <= 262144 for value in receipt["classBytes"].values())
    (out / (z.stem + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt

rows = {str(n): build(n) for n in (29, 30, 31)}
rows["30-reordered"] = dict(rows["30"])
rows["30-reordered"]["entries"] = [rows["30"]["entries"][0], *reversed(rows["30"]["entries"][1:])]
(out / "30-reordered.json").write_text(json.dumps(rows["30-reordered"], indent=2) + "\n")
rows["30-262144"] = build(30, 262144)
rows["30-262145"] = build(30, 262145)
(out / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({key: {"bindingCount": value["bindingCount"], "totalClassBytes": value["totalClassBytes"]} for key, value in rows.items()}, indent=2))
