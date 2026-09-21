#!/usr/bin/env python3
"""Build trusted generated Java-8 guest-stack-trace probes only.

This script never reads an original JAR, Minecraft data, or a world.  The optional
host JVM run is only a differential sanity check for these locally generated
sources; it is not an EVM execution path.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build"
assert out.name.startswith("java-diff-mc-throwable-guest-stack-trace-fixtures-")
assert not out.exists()
out.mkdir()
sources_root = out / "src"; classes_root = out / "classes"
sources_root.mkdir(); classes_root.mkdir()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
rows = {}

def build(label, sources, entries, host_main=None):
    source_dir = sources_root / label; class_dir = classes_root / label
    source_dir.mkdir(); class_dir.mkdir()
    for name, body in sources.items():
        path = source_dir / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", class_dir,
                    *map(str, sorted(source_dir.rglob("*.java")))], check=True)
    if host_main is not None:
        subprocess.run([java, "-cp", class_dir, host_main], check=True)
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for name in entries:
            data = (class_dir / name).read_bytes()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)
    row = {
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": 94,
        "totalClassBytes": sum((class_dir / name).stat().st_size for name in entries),
        "classBytes": {name: (class_dir / name).stat().st_size for name in entries},
        "classSHA256": {name: hashlib.sha256((class_dir / name).read_bytes()).hexdigest() for name in entries},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row

# Top-first caller frames must be leaf, nested, then main.  The checks deliberately
# index all three elements, as ReflectionUtil's prior failure did, then verify the
# two real dotted class/method names and the non-native element API.
stack_source = """public final class GuestStackTraceMain {
  static int result;
  static void leaf() {
    Throwable t = new Throwable();
    StackTraceElement[] a = t.getStackTrace();
    StackTraceElement[] b = t.getStackTrace();
    if (a == null || b == null || a == b || a.length != 3 || b.length != 3) throw new Error();
    if (a[0] == b[0]) throw new Error();
    if (!a[0].getClassName().equals(\"GuestStackTraceMain\") || !a[0].getMethodName().equals(\"leaf\")) throw new Error();
    if (!a[1].getClassName().equals(\"GuestStackTraceMain\") || !a[1].getMethodName().equals(\"nested\")) throw new Error();
    if (!a[2].getClassName().equals(\"GuestStackTraceMain\") || !a[2].getMethodName().equals(\"main\")) throw new Error();
    if (a[0].isNativeMethod() || a[1].isNativeMethod() || a[2].isNativeMethod()) throw new Error();
    result = 7;
  }
  static void nested() { leaf(); }
  public static void main(String[] ignored) { nested(); }
}
"""
# HotSpot may legally reuse immutable host StackTraceElement objects across
# repeated calls, while this bounded guest profile explicitly does not; therefore
# the freshness witness intentionally has no host-identity oracle.
build("guest-stack", {"GuestStackTraceMain.java": stack_source}, ["GuestStackTraceMain.class"])

# A two-frame probe keeps a distinct depth and catches accidental constant
# cardinality/order while remaining host-oracle compatible.
two_source = """public final class GuestStackTraceTwoMain {
  static int result;
  static void leaf() {
    StackTraceElement[] a = new Throwable().getStackTrace();
    if (a.length != 2) throw new Error();
    if (!a[0].getClassName().equals(\"GuestStackTraceTwoMain\") || !a[0].getMethodName().equals(\"leaf\")) throw new Error();
    if (!a[1].getClassName().equals(\"GuestStackTraceTwoMain\") || !a[1].getMethodName().equals(\"main\")) throw new Error();
    result = 7;
  }
  public static void main(String[] ignored) { leaf(); }
}
"""
build("guest-stack-two", {"GuestStackTraceTwoMain.java": two_source}, ["GuestStackTraceTwoMain.class"], "GuestStackTraceTwoMain")

# Thread keeps its separately bounded zero-length Java implementation.  It has no
# host oracle because the host Thread API intentionally has different semantics.
thread_source = """public final class ThreadStackTraceUnchangedMain {
  static int result;
  public static void main(String[] ignored) {
    StackTraceElement[] a = Thread.currentThread().getStackTrace();
    StackTraceElement[] b = Thread.currentThread().getStackTrace();
    if (a == null || b == null || a == b || a.length != 0 || b.length != 0) throw new Error();
    result = 7;
  }
}
"""
build("thread-empty", {"ThreadStackTraceUnchangedMain.java": thread_source}, ["ThreadStackTraceUnchangedMain.class"])

# No Throwable/StackTraceElement active use: both remain absent from initialization
# state even though their fixed bootstrap images are installed.
build("uninitialized", {"UninitializedMain.java": "public final class UninitializedMain { static int result; public static void main(String[] a) { result = 7; } }\n"}, ["UninitializedMain.class"], "UninitializedMain")

# Canonical bootstrap ownership rejection controls.  They are compiled but never
# executed by the host JVM and are supplied only to the generated EVM harness.
build("raw-throwable", {
    "RawThrowableMain.java": "public final class RawThrowableMain { public static void main(String[] a) {} }\n",
    "java/lang/Throwable.java": "package java.lang; public class Throwable { public Throwable() {} }\n",
}, ["RawThrowableMain.class", "java/lang/Throwable.class"])
build("raw-stack-trace-element", {
    "RawStackTraceElementMain.java": "public final class RawStackTraceElementMain { public static void main(String[] a) {} }\n",
    "java/lang/StackTraceElement.java": "package java.lang; public final class StackTraceElement { public StackTraceElement() {} }\n",
}, ["RawStackTraceElementMain.class", "java/lang/StackTraceElement.class"])

(out / "fixtures.json").write_text(json.dumps(rows, indent=2) + "\n")
