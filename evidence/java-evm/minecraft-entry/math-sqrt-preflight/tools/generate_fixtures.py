#!/usr/bin/env python3
"""Generate only trusted Java-8 Math.sqrt and retained fixtures.

The host JVM is an oracle for generated positive Java sources only. It never
loads an original class/JAR/resource and never supplies an EVM result.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-math-sqrt-fixtures-") and not out.exists()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
out.mkdir(); source_root = out / "src"; classes_root = out / "classes"
source_root.mkdir(); classes_root.mkdir(); rows = {}


def build(label, sources, entries, host_main=None, mutate=None):
    src = source_root / label; classes = classes_root / label
    src.mkdir(); classes.mkdir()
    for name, text in sources.items():
        path = src / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                    *map(str, sorted(src.rglob("*.java")))], check=True)
    if host_main:
        subprocess.run([java, "-cp", classes, host_main], check=True)
    payloads = {}
    for name in entries:
        data = (classes / name).read_bytes()
        payloads[name] = mutate(name, data) if mutate else data
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zipped:
        for name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            zipped.writestr(info, payloads[name])
    row = {
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": 96,
        "totalClassBytes": sum(len(data) for data in payloads.values()),
        "classBytes": {name: len(data) for name, data in payloads.items()},
        "classSHA256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None, "selectedResource": None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row


# Every listed ASCII shape is independently run by Java 8. The identity tests
# distinguish no-change returns (including empty) from lower-case copy results.
build("lower-ascii", {
    "LowerAsciiMain.java": """import java.util.Locale;
public final class LowerAsciiMain {
  static int result;
  static void same(String got, String want) { if (!got.equals(want)) throw new Error(); }
  public static void main(String[] ignored) {
    Locale root = Locale.ROOT;
    if (root == null || root != Locale.ROOT) throw new Error();
    String empty = new String(new char[0]);
    if (empty.toLowerCase(root) != empty) throw new Error();
    String lower = new String(new char[] { 'a', 'z', '-', '0', '!' });
    if (lower.toLowerCase(root) != lower) throw new Error();
    String upper = new String(new char[] { 'A', 'Z' });
    String upperResult = upper.toLowerCase(root);
    if (upperResult == upper) throw new Error();
    same(upperResult, "az");
    if (upperResult.hashCode() != "az".hashCode()) throw new Error();
    String mixed = new String(new char[] { 'A', 'b', 'C', '-', 'Z' });
    String mixedResult = mixed.toLowerCase(root);
    if (mixedResult == mixed) throw new Error();
    same(mixedResult, "abc-z");
    String punctuation = new String(new char[] { '1', '2', '!', '@', '[', '`', '{', '~' });
    if (punctuation.toLowerCase(root) != punctuation) throw new Error();
    result = 7;
  }
}
""",
}, ["LowerAsciiMain.class"], "LowerAsciiMain")

# Guest catchability is tested separately from the terminal NPE below.
build("lower-null-caught", {
    "LowerNullCaughtMain.java": """import java.util.Locale;
public final class LowerNullCaughtMain {
  static int result;
  public static void main(String[] ignored) {
    String value = new String(new char[] { 'A' });
    try { value.toLowerCase((Locale) null); throw new Error(); }
    catch (NullPointerException expected) {
      if (!value.equals("A") || value.toLowerCase(Locale.ROOT) == value) throw new Error();
      result = 7;
    }
  }
}
""",
}, ["LowerNullCaughtMain.class"], "LowerNullCaughtMain")

# This is deliberately not passed to host java: its required EVM terminal is a
# guest NPE record, while the generated source itself remains Java-8-valid.
build("lower-null-uncaught", {
    "LowerNullUncaughtMain.java": """import java.util.Locale;
public final class LowerNullUncaughtMain {
  public static void main(String[] ignored) {
    new String(new char[] { 'A' }).toLowerCase((Locale) null);
  }
}
""",
}, ["LowerNullUncaughtMain.class"])

# Non-ASCII is intentionally a bounded profile refusal, not a host Unicode
# oracle result. The leading ASCII upper-case catches accidental early writes.
build("lower-non-ascii-refusal", {
    "LowerNonAsciiRefusalMain.java": """import java.util.Locale;
public final class LowerNonAsciiRefusalMain {
  public static void main(String[] ignored) {
    new String(new char[] { 'A', '\u00e9' }).toLowerCase(Locale.ROOT);
  }
}
""",
}, ["LowerNonAsciiRefusalMain.class"])

# The exact upper-case overload remains absent and must resolve/refuse honestly.
build("upper-omitted", {
    "UpperOmittedMain.java": """import java.util.Locale;
public final class UpperOmittedMain {
  public static void main(String[] ignored) {
    new String(new char[] { 'a' }).toUpperCase(Locale.ROOT);
  }
}
""",
}, ["UpperOmittedMain.class"])

# Bootstrap ownership prevents raw replacement of either input owner.
build("raw-string-replacement", {
    "RawStringReplacementMain.java": "public final class RawStringReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/String.java": "package java.lang; public final class String { public String() {} }\n",
}, ["RawStringReplacementMain.class", "java/lang/String.class"])
build("raw-locale-replacement", {
    "RawLocaleReplacementMain.java": "public final class RawLocaleReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/Locale.java": "package java.util; public final class Locale { public static final Locale ROOT = null; private Locale() {} }\n",
}, ["RawLocaleReplacementMain.class", "java/util/Locale.class"])

# Retained independent ordinary guest controls, all with Java-8 host oracles.
build("locale-root", {
    "LocaleRootMain.java": """import java.util.Locale;
public final class LocaleRootMain { static int result; public static void main(String[] ignored) {
  Locale a = Locale.ROOT, b = Locale.ROOT;
  if (a == null || a != b || !(a instanceof Locale)) throw new Error(); result = 7;
} }
""",
}, ["LocaleRootMain.class"], "LocaleRootMain")
build("retained-string", {
    "RetainedStringMain.java": """public final class RetainedStringMain { static int result; public static void main(String[] ignored) {
  String value = new String(new char[] { 'a', 'B', '-', 'c' });
  if (value.indexOf('B') != 1 || !value.substring(1).equals("B-c") || value != value.intern()) throw new Error(); result = 7;
} }
""",
}, ["RetainedStringMain.class"], "RetainedStringMain")
build("retained-map", {
    "RetainedMapMain.java": """import java.util.Map; import java.util.concurrent.ConcurrentHashMap;
public final class RetainedMapMain { static int result; public static void main(String[] ignored) {
  Map<Object,Object> map = new ConcurrentHashMap<Object,Object>(); Object k = new Object(), a = new Object(), b = new Object();
  Map.Entry<Object,Object> entry = (Map.Entry<Object,Object>) null;
  if (entry != null || map.put(k,a) != null || map.get(k) != a || map.put(k,b) != a || map.get(k) != b || map.size() != 1) throw new Error(); result = 7;
} }
""",
}, ["RetainedMapMain.class"], "RetainedMapMain")
build("retained-integer", {
    "RetainedIntegerMain.java": """public final class RetainedIntegerMain { static int result; public static void main(String[] ignored) {
  if (Integer.highestOneBit(0) != 0 || Integer.highestOneBit(0x7fffffff) != 0x40000000 || Integer.highestOneBit(-1) != 0x80000000) throw new Error(); result = 7;
} }
""",
}, ["RetainedIntegerMain.class"], "RetainedIntegerMain")

# Exact System.identityHashCode(Object) coverage.  The return values are saved
# as ordinary guest statics so the generated-only gate can compare them against
# the decoded guest heap ordinals without using host identity.  The override
# throws if any implementation dispatches Object.hashCode instead of using the
# already-existing guest reference handle.
build("identity-hash", {
    "IdentityHashMain.java": """public final class IdentityHashMain {
  static int nullValue, first, firstAgain, second, array, arrayAgain, mirror, mirrorAgain, overridden, result;
  public static void main(String[] ignored) {
    Object one = new Object(); Object two = new Object(); Object[] values = new Object[1];
    Class<?> type = IdentityHashMain.class; Object custom = new IdentityHashOverride();
    nullValue = System.identityHashCode(null);
    first = System.identityHashCode(one); firstAgain = System.identityHashCode(one);
    second = System.identityHashCode(two); array = System.identityHashCode(values); arrayAgain = System.identityHashCode(values);
    mirror = System.identityHashCode(type); mirrorAgain = System.identityHashCode(type); overridden = System.identityHashCode(custom);
    if (nullValue != 0 || first == 0 || first != firstAgain || second == 0 || second == first || array == 0 || array != arrayAgain || mirror == 0 || mirror != mirrorAgain || overridden == 0) throw new Error();
    if (first == array || first == mirror || first == overridden || second == array || second == mirror || second == overridden || array == mirror || array == overridden || mirror == overridden) throw new Error();
    result = 7;
  }
}
""",
    "IdentityHashOverride.java": """final class IdentityHashOverride {
  public int hashCode() { throw new Error(); }
}
""",
}, ["IdentityHashMain.class", "IdentityHashOverride.class"], "IdentityHashMain")

# This has the same raw class order, System initialization, ordinary/array/
# Class-mirror/override allocations and terminal state shape, but it makes no
# identityHashCode invocation.  The gate requires an identical heap and System
# static state after q1/q7/direct/reopen, proving binding17 did not allocate or
# mutate state.
build("identity-no-mutation-control", {
    "IdentityHashCtrl.java": """public final class IdentityHashCtrl {
  static int result;
  public static void main(String[] ignored) {
    Object one = new Object(); Object two = new Object(); Object[] values = new Object[1];
    Class<?> type = IdentityHashCtrl.class; Object custom = new IdentityHashControlOverride();
    System.currentTimeMillis();
    if (one == two || values == null || type == null || custom == null) throw new Error(); result = 7;
  }
}
""",
    "IdentityHashControlOverride.java": """final class IdentityHashControlOverride {
  public int hashCode() { throw new Error(); }
}
""",
}, ["IdentityHashCtrl.class", "IdentityHashControlOverride.class"], "IdentityHashCtrl")

# Both omitted APIs are Java-8-valid sources but intentionally receive no host
# oracle result: Object.hashCode and every unlisted System API remain absent.
build("object-hashcode-omitted", {
    "ObjectHashCodeOmittedMain.java": """public final class ObjectHashCodeOmittedMain { public static void main(String[] ignored) { new Object().hashCode(); } }\n""",
}, ["ObjectHashCodeOmittedMain.class"])
build("system-general-omitted", {
    "SystemGeneralOmittedMain.java": """public final class SystemGeneralOmittedMain { public static void main(String[] ignored) { System.gc(); } }\n""",
}, ["SystemGeneralOmittedMain.class"])

# Bootstrap ownership remains exact: a raw same-named System is refused before
# it can obtain binding17 or alter the canonical System image.
build("raw-system-replacement", {
    "RawSystemReplacementMain.java": """public final class RawSystemReplacementMain { public static void main(String[] ignored) {} }\n""",
    "java/lang/System.java": """package java.lang; public final class System { public static native int identityHashCode(Object value); private System() {} }\n""",
}, ["RawSystemReplacementMain.class", "java/lang/System.class"])

# The existing out/err native cells retain their exact isolation from binding17.
build("retained-system-out-err", {
    "RetainedSystemOutErrMain.java": """import java.io.PrintStream;
public final class RetainedSystemOutErrMain { static int result; public static void main(String[] ignored) {
  PrintStream oldOut = System.out, oldErr = System.err;
  if (oldOut == null || oldErr == null || oldOut == oldErr) throw new Error();
  System.setOut(null); if (System.out != null || System.err != oldErr) throw new Error();
  System.setErr(null); if (System.err != null) throw new Error();
  System.setOut(oldOut); System.setErr(oldErr);
  if (System.out != oldOut || System.err != oldErr) throw new Error(); result = 7;
} }
""",
}, ["RetainedSystemOutErrMain.class"], "RetainedSystemOutErrMain")

# Correct-rounding binary64 witnesses are bit-safe: the generated Java-8 oracle
# runs the same source, but the EVM asserts raw Double bits through bindings3/4.
# Inputs include exact squares, irrational neighbours around powers, normal and
# subnormal extrema, and values adjacent to rounding boundaries.
build("math-sqrt-binary64", {
    "MathSqrtMain.java": """public final class MathSqrtMain {
  static int result;
  static void exact(long input, long expected) {
    long got = Double.doubleToRawLongBits(Math.sqrt(Double.longBitsToDouble(input)));
    if (got != expected) throw new Error();
  }
  static void quietNaN(long input) {
    long got = Double.doubleToRawLongBits(Math.sqrt(Double.longBitsToDouble(input)));
    if ((got & 0x7ff0000000000000L) != 0x7ff0000000000000L ||
        (got & 0x000fffffffffffffL) == 0 || (got & 0x0008000000000000L) == 0) throw new Error();
  }
  public static void main(String[] ignored) {
    // signed zeros, exact squares, and irrational values / immediate neighbours.
    exact(0x0000000000000000L, 0x0000000000000000L);
    exact(0x8000000000000000L, 0x8000000000000000L);
    exact(0x3ff0000000000000L, 0x3ff0000000000000L);
    exact(0x4000000000000000L, 0x3ff6a09e667f3bcdL);
    exact(0x4008000000000000L, 0x3ffbb67ae8584caaL);
    exact(0x3ff0000000000001L, 0x3ff0000000000000L);
    exact(0x3fefffffffffffffL, 0x3fefffffffffffffL);
    exact(0x3ff0000000000002L, 0x3ff0000000000001L);
    exact(0x3feffffffffffffeL, 0x3fefffffffffffffL);
    exact(0x3ff0000000000003L, 0x3ff0000000000001L);
    exact(0x4010000000000000L, 0x4000000000000000L);
    exact(0x400fffffffffffffL, 0x3fffffffffffffffL);
    // normal/subnormal extrema and powers with a carry-sensitive significand.
    exact(0x0010000000000000L, 0x2000000000000000L);
    exact(0x0010000000000001L, 0x2000000000000000L);
    exact(0x000fffffffffffffL, 0x1fffffffffffffffL);
    exact(0x0000000000000001L, 0x1e60000000000000L);
    exact(0x0000000000000002L, 0x1e66a09e667f3bcdL);
    exact(0x7fefffffffffffffL, 0x5fefffffffffffffL);
    exact(0x7fe0000000000000L, 0x5fe6a09e667f3bcdL);
    exact(0x4340000000000000L, 0x4196a09e667f3bcdL);
    exact(0x3cb0000000000000L, 0x3e50000000000000L);
    exact(0x3fd0000000000000L, 0x3fe0000000000000L);
    // positive infinity is fixed; all NaN/negative nonzero categories are qNaN.
    exact(0x7ff0000000000000L, 0x7ff0000000000000L);
    quietNaN(0x7ff0000000000001L); quietNaN(0x7ff8000000001234L);
    quietNaN(0xbff0000000000000L); quietNaN(0xfff0000000000000L);
    result = 7;
  }
}
""",
}, ["MathSqrtMain.class"], "MathSqrtMain")

# The existing guest Properties construction remains live and exact.
build("retained-properties", {
    "RetainedPropertiesMain.java": """public final class RetainedPropertiesMain { static int result;
  public static void main(String[] ignored) { String value = System.getProperty("java.version");
    if (value == null || !value.equals("1.8")) throw new Error(); result = 7; }
}
""",
}, ["RetainedPropertiesMain.class"])

# Owner reservation, omitted siblings and StrictMath remain honest refusals.
build("raw-math-replacement", {
    "RawMathReplacementMain.java": "public final class RawMathReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/Math.java": "package java.lang; public final class Math { private Math() {} public static native double sqrt(double value); }\n",
}, ["RawMathReplacementMain.class", "java/lang/Math.class"])
build("math-cbrt-omitted", {
    "MathCbrtOmittedMain.java": "public final class MathCbrtOmittedMain { public static void main(String[] ignored) { Math.cbrt(8.0); } }\n",
}, ["MathCbrtOmittedMain.class"])
build("strictmath-sqrt-omitted", {
    "StrictMathSqrtOmittedMain.java": "public final class StrictMathSqrtOmittedMain { public static void main(String[] ignored) { StrictMath.sqrt(4.0); } }\n",
}, ["StrictMathSqrtOmittedMain.class"])

# Retain String/Map/Integer controls and cover raw71 aggregate-byte frontiers. The eight padding locations
# keep each individual locally generated class below the DI0 per-input bound.
def count_source(count, pads=()):
    tails = count - 1
    calls = " + ".join("Tail%02d.touch()" % index for index in range(1, tails + 1))
    fields = "".join("  private static final String PAD%02d = \"%s\";\n" % (index, value) for index, value in enumerate(pads))
    return """public final class CountMain {
%s  static int sentinel;
  public static void main(String[] ignored) { sentinel = %s; if (sentinel != %d) throw new Error(); }
}
""" % (fields, calls, tails * (tails + 1) // 2)

def tail_source(index, pads=()):
    fields = "".join("  private static final String PAD%02d = \"%s\";\n" % (number, value) for number, value in enumerate(pads))
    return "final class Tail%02d {\n%s  static int touch() { return %d; }\n}\n" % (index, fields, index)

def count_fixture(label, count, target=None):
    src = source_root / label; classes = classes_root / label
    src.mkdir(); classes.mkdir()
    for index in range(1, count): (src / ("Tail%02d.java" % index)).write_text(tail_source(index))
    def compile(pads=()):
        (src / "CountMain.java").write_text(count_source(count, pads[:1]))
        for index in range(1, 8): (src / ("Tail%02d.java" % index)).write_text(tail_source(index, pads[index:index + 1]))
        shutil.rmtree(classes); classes.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes, *map(str, sorted(src.glob("*.java")))], check=True)
        return sum(candidate.stat().st_size for candidate in classes.glob("*.class"))
    total = compile()
    if target is not None:
        assert total < target
        overhead = compile([""] * 8); need = target - total - (overhead - total)
        assert 0 <= need <= 8 * 65000
        pads = [(chr(65 + index) + "x" * (amount - 1)) if amount else "" for index, amount in enumerate(need // 8 + (1 if index < need % 8 else 0) for index in range(8))]
        total = compile(pads)
        for _ in range(3):
            delta = target - total
            if delta == 0: break
            index = max(range(8), key=lambda item: len(pads[item]))
            assert 0 <= len(pads[index]) + delta <= 65000
            pads[index] = pads[index][:len(pads[index]) + delta] if delta < 0 else pads[index] + "x" * delta
            total = compile(pads)
        assert total == target, (label, total, target)
        assert max(candidate.stat().st_size for candidate in classes.glob("*.class")) <= 262144
    else:
        subprocess.run([java, "-cp", classes, "CountMain"], check=True)
    entries = ["CountMain.class"] + ["Tail%02d.class" % index for index in range(1, count)]
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zipped:
        for name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            zipped.writestr(info, (classes / name).read_bytes())
    row = {"entries": entries, "bindingCount": count, "bootstrapCount": 96, "totalClassBytes": total,
           "classBytes": {name: (classes / name).stat().st_size for name in entries},
           "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
           "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(), "java8HostOracle": target is None, "selectedResource": None}
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n"); rows[label] = row

count_fixture("count-71", 71)
count_fixture("count-72", 72)
count_fixture("count-71-471911", 71, 471911)
count_fixture("count-71-471912", 71, 471912)

(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [71, 471911], "fixtures": rows,
    "scope": "generated Java-8 System.identityHashCode(Object), retained System/String/Locale/Map/Integer controls, and raw71 capacity boundaries only; no original/JAR/resource/network/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
