#!/usr/bin/env python3
"""Generate trusted Java-8 sparse-array stress and retained fixtures.

The host JVM runs generated fixtures only; it never opens an original class,
JAR, resource, network input, world, or EULA data.
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-math-cos-fixtures-") and not out.exists()
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
    if mutate:
        for name in entries:
            path = classes / name
            path.write_bytes(mutate(name, path.read_bytes()))
    host_output = None
    if host_main:
        completed = subprocess.run([java, "-cp", classes, host_main], check=True,
                                   capture_output=True, text=True)
        host_output = completed.stdout.splitlines()
    payloads = {name: (classes / name).read_bytes() for name in entries}
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zipped:
        for name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            zipped.writestr(info, payloads[name])
    row = {
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": 97,
        "totalClassBytes": sum(len(data) for data in payloads.values()),
        "classBytes": {name: len(data) for name, data in payloads.items()},
        "classSHA256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None, "hostOutput": host_output,
        "selectedResource": None,
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

# Generated-only Math.sin verification vectors. The one exact genuine Minecraft
# argument is included as an ordinary guest input; the other points are test-only.
# No expected output enters EVM execution. A separate Java 8 host-only class emits
# raw result witnesses into fixture metadata for post-execution comparison.
import hashlib as _hashlib
_oracle_path = root / "evidence/java-evm/minecraft-entry/math-sin-independent-oracle/results/samples.tsv"
assert _hashlib.sha256(_oracle_path.read_bytes()).hexdigest() == "6001a5c714608ca9649b08b25eba27a3aa011f7c870a32ddae15ca330fefc058"
_oracle = {}
with _oracle_path.open("r", encoding="ascii", newline="") as _stream:
    next(_stream)
    for _line in _stream:
        _f = _line.rstrip("\n").split("\t")
        if len(_f) == 5:
            _oracle[(_f[0], _f[1])] = (int(_f[2], 16), int(_f[3], 16), int(_f[4], 16))

def add_sin_fixture(label, vectors):
    guest_fields = "".join("  static long d%d;\n" % i for i in range(len(vectors)))
    guest_fields += "".join("  static int f%d;\n" % i for i in range(len(vectors)))
    guest_body = []
    host_body = []
    for i, (name, raw) in enumerate(vectors):
        lit = "0x%016xL" % raw
        expr = "Double.longBitsToDouble(%s)" % lit
        guest_body.append("    double x%d = Math.sin(%s); d%d = Double.doubleToRawLongBits(x%d); f%d = Float.floatToRawIntBits((float)x%d);" % (i, expr, i, i, i, i))
        host_body.append("    double x%d = Math.sin(%s); System.out.println(\"%s\\t%016x\\t\" + Long.toHexString(Double.doubleToRawLongBits(x%d)) + \"\\t\" + Integer.toHexString(Float.floatToRawIntBits((float)x%d)));" % (i, expr, name, raw, i, i))
    guest = "public final class MathSinBoundedMain {\n" + guest_fields + "  static int result;\n  public static void main(String[] ignored) {\n" + "\n".join(guest_body) + "\n    result = 7;\n  }\n}\n"
    host = "public final class SinHostOracle {\n  public static void main(String[] ignored) {\n" + "\n".join(host_body) + "\n  }\n}\n"
    build(label, {"MathSinBoundedMain.java": guest, "SinHostOracle.java": host},
          ["MathSinBoundedMain.class"], "SinHostOracle")
    fixture_row = rows[label]
    expected = []
    for line in fixture_row["hostOutput"]:
        name, raw, dbits, fbits = line.split("\t")
        expected.append({"name": name, "inputRaw": raw, "javaDoubleRaw": dbits.zfill(16), "javaFloatRaw": fbits.zfill(8)})
    assert len(expected) == len(vectors)
    fixture_row["sinVectors"] = expected
    (out / (label + ".json")).write_text(json.dumps(fixture_row, indent=2) + "\n")

# The measured nonzero raw value is precisely the original guest stack value.
# Edges include both zeros, subnormals/normals, the proven identity threshold,
# its successor, pi/2, pi, and the inclusive largest finite in-domain encoding.
edge_names = [
    "positive-zero", "negative-zero", "positive-min-subnormal", "negative-min-subnormal",
    "positive-min-normal", "negative-min-normal", "pi-over-2-below", "pi-over-2-nearest",
    "pi-over-2-above", "pi-below", "pi-nearest", "pi-above", "two-pi-below", "two-pi-nearest",
]
edge_vectors = [(name, _oracle[("EDGE", name)][0]) for name in edge_names]
edge_vectors.append(("two-pi-nearest-negative", 0xc01921fb54442d18))
edge_vectors.extend([
    ("identity-cutoff-positive", 0x3e30000000000000),
    ("identity-cutoff-negative", 0xbe30000000000000),
    ("identity-successor-positive", 0x3e30000000000001),
    ("identity-successor-negative", 0xbe30000000000001),
    ("measured-positive", 0x3f1921fb54442d18),
    ("measured-negative", 0xbf1921fb54442d18),
])
add_sin_fixture("math-sin-bounded-edges", edge_vectors)

# Seventeen widely spaced deterministic generated-grid points, mirrored to the
# negative interval. These are sampled EVM executions, not output-table entries.
grid_indices = [1] + list(range(4096, 65536, 4096)) + [65535]
grid_vectors = []
for index in grid_indices:
    raw = _oracle[("GRID", str(index))][0]
    grid_vectors.append(("grid-%d-positive" % index, raw))
    grid_vectors.append(("grid-%d-negative" % index, raw | 0x8000000000000000))
add_sin_fixture("math-sin-bounded-grid", grid_vectors)

# Bounded Math.asin uses raw binary64 oracle witnesses from the separately
# generated OpenJDK 8 dataset. These selected k/256 controls complement exact
# branch/endpoint/tiny edges; no oracle output is an EVM input.
_asin_oracle = {}
_asin_sample_path = Path(__file__).resolve().parents[5] / "evidence/java-evm/minecraft-entry/math-asin-independent-oracle/results/samples.tsv"
with _asin_sample_path.open("r", encoding="ascii", newline="") as _stream:
    assert _stream.readline().startswith("# generated OpenJDK 8 oracle;")
    assert _stream.readline().rstrip("\n") == "categories\tinput_bits\tpolicy\tasin_bits\tfloat_bits"
    for _line in _stream:
        _categories, _raw, _policy, _asin, _float = _line.rstrip("\n").split("\t")
        if _policy == "SUPPORTED":
            _asin_oracle[int(_raw, 16)] = (int(_asin, 16), int(_float, 16))

def add_asin_fixture(label, vectors):
    guest_fields = "".join("  static long d%d;\n" % i for i in range(len(vectors)))
    guest_fields += "".join("  static int f%d;\n" % i for i in range(len(vectors)))
    guest_body = []
    host_body = []
    def oracle_for(raw):
        if raw in _asin_oracle: return _asin_oracle[raw]
        magnitude = raw & 0x7fffffffffffffff
        assert magnitude in _asin_oracle, hex(raw)
        dbits, fbits = _asin_oracle[magnitude]
        return (dbits | (raw & 0x8000000000000000), fbits | ((raw >> 32) & 0x80000000))
    for i, (name, raw) in enumerate(vectors):
        expected_oracle = oracle_for(raw)
        lit = "0x%016xL" % raw
        expr = "Double.longBitsToDouble(%s)" % lit
        guest_body.append("    double y%d = Math.asin(%s); d%d = Double.doubleToRawLongBits(y%d); f%d = Float.floatToRawIntBits((float)y%d);" % (i, expr, i, i, i, i))
        host_body.append("    double y%d = Math.asin(%s); System.out.println(\"%s\\t%016x\\t\" + Long.toHexString(Double.doubleToRawLongBits(y%d)) + \"\\t\" + Integer.toHexString(Float.floatToRawIntBits((float)y%d)));" % (i, expr, name, raw, i, i))
    guest = "public final class MathAsinBoundedMain {\n" + guest_fields + "  static int result;\n  public static void main(String[] ignored) {\n" + "\n".join(guest_body) + "\n    result = 7;\n  }\n}\n"
    host = "public final class AsinHostOracle {\n  public static void main(String[] ignored) {\n" + "\n".join(host_body) + "\n  }\n}\n"
    build(label, {"MathAsinBoundedMain.java": guest, "AsinHostOracle.java": host},
          ["MathAsinBoundedMain.class"], "AsinHostOracle")
    expected = []
    for line in rows[label]["hostOutput"]:
        name, raw, dbits, fbits = line.split("\t")
        expected.append({"name": name, "inputRaw": raw, "javaDoubleRaw": dbits.zfill(16), "javaFloatRaw": fbits.zfill(8)})
        oracle = oracle_for(int(raw, 16))
        assert int(dbits, 16) == oracle[0] and int(fbits, 16) == oracle[1]
    assert len(expected) == len(vectors)
    rows[label]["asinVectors"] = expected
    (out / (label + ".json")).write_text(json.dumps(rows[label], indent=2) + "\n")

_asin_vectors = [("positive-zero", 0x0000000000000000), ("negative-zero", 0x8000000000000000),
                 ("positive-min-subnormal", 0x0000000000000001), ("negative-min-subnormal", 0x8000000000000001),
                 ("positive-max-subnormal", 0x000fffffffffffff), ("negative-max-subnormal", 0x800fffffffffffff),
                 ("positive-min-normal", 0x0010000000000000), ("negative-min-normal", 0x8010000000000000),
                 ("tiny-cutoff-positive", 0x3e40000000000000), ("tiny-cutoff-negative", 0xbe40000000000000),
                 ("tiny-successor-positive", 0x3e40000000000001), ("tiny-successor-negative", 0xbe40000000000001),
                 ("half-below", 0x3fdfffffffffffff), ("half-exact", 0x3fe0000000000000),
                 ("half-above", 0x3fe0000000000001), ("half-below-negative", 0xbfdfffffffffffff),
                 ("half-exact-negative", 0xbfe0000000000000), ("half-above-negative", 0xbfe0000000000001),
                 ("one-below", 0x3fefffffffffffff), ("one-two-below", 0x3feffffffffffffe),
                 ("one", 0x3ff0000000000000), ("negative-one-below", 0xbfefffffffffffff),
                 ("negative-one", 0xbff0000000000000)]
for k in (1, 32, 64, 127, 128, 129, 192, 224, 255, 256):
    raw = int.from_bytes(__import__("struct").pack(">d", k / 256.0), "big")
    _asin_vectors.extend([("k%d/256-positive" % k, raw), ("k%d/256-negative" % k, raw | 0x8000000000000000)])
add_asin_fixture("math-asin-bounded-edges", _asin_vectors)

# Bounded Math.cos uses raw binary64 inputs. The independent Java 8 host class
# emits only post-execution witnesses; its outputs are never included in EVM input.
import math as _math
import random as _random
import struct as _struct

def _double_raw(value):
    return int.from_bytes(_struct.pack(">d", value), "big")

def add_cos_fixture(label, vectors):
    guest_fields = "".join("  static long d%d;\n" % i for i in range(len(vectors)))
    guest_fields += "".join("  static int f%d;\n" % i for i in range(len(vectors)))
    guest_body, host_body = [], []
    for i, (name, raw) in enumerate(vectors):
        lit = "0x%016xL" % raw
        expr = "Double.longBitsToDouble(%s)" % lit
        guest_body.append("    double y%d = Math.cos(%s); d%d = Double.doubleToRawLongBits(y%d); f%d = Float.floatToRawIntBits((float)y%d);" % (i, expr, i, i, i, i))
        host_body.append("    double y%d = Math.cos(%s); System.out.println(\"%s\\t%016x\\t\" + Long.toHexString(Double.doubleToRawLongBits(y%d)) + \"\\t\" + Integer.toHexString(Float.floatToRawIntBits((float)y%d)));" % (i, expr, name, raw, i, i))
    guest = "public final class MathCosBoundedMain {\n" + guest_fields + "  static int result;\n  public static void main(String[] ignored) {\n" + "\n".join(guest_body) + "\n    result = 7;\n  }\n}\n"
    host = "public final class CosHostOracle {\n  public static void main(String[] ignored) {\n" + "\n".join(host_body) + "\n  }\n}\n"
    build(label, {"MathCosBoundedMain.java": guest, "CosHostOracle.java": host},
          ["MathCosBoundedMain.class"], "CosHostOracle")
    expected = []
    for line in rows[label]["hostOutput"]:
        name, raw, dbits, fbits = line.split("\t")
        expected.append({"name": name, "inputRaw": raw, "javaDoubleRaw": dbits.zfill(16), "javaFloatRaw": fbits.zfill(8)})
    assert len(expected) == len(vectors)
    rows[label]["cosVectors"] = expected
    (out / (label + ".json")).write_text(json.dumps(rows[label], indent=2) + "\n")

_cos_vectors = [
    ("positive-zero", 0x0000000000000000), ("negative-zero", 0x8000000000000000),
    ("positive-min-subnormal", 0x0000000000000001), ("negative-min-subnormal", 0x8000000000000001),
    ("positive-max-subnormal", 0x000fffffffffffff), ("negative-max-subnormal", 0x800fffffffffffff),
    ("positive-min-normal", 0x0010000000000000), ("negative-min-normal", 0x8010000000000000),
    ("tiny-cutoff-positive", 0x3e40000000000000), ("tiny-cutoff-negative", 0xbe40000000000000),
    ("tiny-successor-positive", 0x3e40000000000001), ("tiny-successor-negative", 0xbe40000000000001),
    ("pi-over-two-below", 0x3ff921fb54442d17), ("pi-over-two-nearest", 0x3ff921fb54442d18),
    ("pi-over-two-above", 0x3ff921fb54442d19),
    ("negative-pi-over-two-below", 0xbff921fb54442d17),
    ("negative-pi-over-two-nearest", 0xbff921fb54442d18),
    ("negative-pi-over-two-above", 0xbff921fb54442d19),
    ("pi-below", 0x400921fb54442d17), ("pi-nearest", 0x400921fb54442d18),
    ("pi-above", 0x400921fb54442d19),
    ("three-pi-over-two-below", 0x4012d97c7f3321d1),
    ("three-pi-over-two-nearest", 0x4012d97c7f3321d2),
    ("three-pi-over-two-above", 0x4012d97c7f3321d3),
    ("two-pi-below", 0x401921fb54442d17), ("two-pi-inclusive-bound", 0x401921fb54442d18),
    ("negative-two-pi-inclusive-bound", 0xc01921fb54442d18),
]
# Exhaustive selected k/256 values span the complete accepted interval; mirror
# signs and add seeded uniformly distributed binary64 encodings as independent checks.
for k in range(0, 1609, 32):
    raw = _double_raw(k / 256.0)
    _cos_vectors.append(("k%d/256-positive" % k, raw))
    if k:
        _cos_vectors.append(("k%d/256-negative" % k, raw | 0x8000000000000000))
_cos_rng = _random.Random(0xC05E120)
for i in range(48):
    value = _cos_rng.uniform(-6.283185307179586, 6.283185307179586)
    _cos_vectors.append(("seeded-raw-%02d" % i, _double_raw(value)))
add_cos_fixture("math-cos-bounded-domain", _cos_vectors)

# Every refusal is an exact call made from a guest class. Invalid inputs cover
# the adjacent out-of-domain raw value, both signs, all nonfinite categories.
for label, class_name, bits in (
    ("math-cos-above-bound-refusal", "MathCosAboveBoundRefusal", "0x401921fb54442d19L"),
    ("math-cos-below-negative-bound-refusal", "MathCosBelowNegativeBoundRefusal", "0xc01921fb54442d19L"),
    ("math-cos-nan-refusal", "MathCosNaNRefusal", "0x7ff8000000001234L"),
    ("math-cos-positive-infinity-refusal", "MathCosPositiveInfinityRefusal", "0x7ff0000000000000L"),
    ("math-cos-negative-infinity-refusal", "MathCosNegativeInfinityRefusal", "0xfff0000000000000L"),
):
    build(label, {class_name + ".java": "public final class %s { static int progress; public static void main(String[] ignored) { for (int i=0;i<24;i++) progress+=i; Math.cos(Double.longBitsToDouble(%s)); } }\n" % (class_name, bits)}, [class_name + ".class"])

# Explicit domain refusals must occur before a result is written or checkpoint
# published; NaN payloads and infinities have no host oracle value.
for label, class_name, bits in (
    ("math-asin-above-bound-refusal", "MathAsinAboveBoundRefusal", "0x3ff0000000000001L"),
    ("math-asin-below-negative-bound-refusal", "MathAsinBelowNegativeBoundRefusal", "0xbff0000000000001L"),
    ("math-asin-nan-refusal", "MathAsinNaNRefusal", "0x7ff8000000001234L"),
    ("math-asin-positive-infinity-refusal", "MathAsinPositiveInfinityRefusal", "0x7ff0000000000000L"),
    ("math-asin-negative-infinity-refusal", "MathAsinNegativeInfinityRefusal", "0xfff0000000000000L"),
):
    build(label, {class_name + ".java": "public final class %s { static int progress; public static void main(String[] ignored) { for (int i=0;i<24;i++) progress+=i; Math.asin(Double.longBitsToDouble(%s)); } }\n" % (class_name, bits)}, [class_name + ".class"])

# These unsupported values must refuse atomically: the first binary64 just above
# the inclusive magnitude bound, its negative, NaN, and both infinities.
for label, class_name, bits in (
    ("math-sin-above-bound-refusal", "MathSinAboveBoundRefusal", "0x401921fb54442d19L"),
    ("math-sin-below-negative-bound-refusal", "MathSinBelowNegativeBoundRefusal", "0xc01921fb54442d19L"),
    ("math-sin-nan-refusal", "MathSinNaNRefusal", "0x7ff8000000001234L"),
    ("math-sin-positive-infinity-refusal", "MathSinPositiveInfinityRefusal", "0x7ff0000000000000L"),
    ("math-sin-negative-infinity-refusal", "MathSinNegativeInfinityRefusal", "0xfff0000000000000L"),
):
    build(label, {
        class_name + ".java": "public final class %s { static int progress; public static void main(String[] ignored) { for (int i=0;i<24;i++) progress+=i; Math.sin(Double.longBitsToDouble(%s)); } }\n" % (class_name, bits),
    }, [class_name + ".class"])

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
    "java/lang/Math.java": "package java.lang; public final class Math { private Math() {} public static native double sqrt(double value); public static native double sin(double value); public static native double asin(double value); }\n",
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

# Actual primitive/reference-array checkpoint stress. A required float[65536]
# plus int[65536] and double[65536] prove empty, one-cell, and distant multi-cell
# sparse records; later Java stores execute after q1/q7 restores. Small arrays
# and Object[] remain dense.
build("sparse-array-stress", {
    "SparseArrayMain.java": """public final class SparseArrayMain {
  static int result;
  static float[] zero, small, dense;
  static int[] one;
  static double[] many;
  static Object[] references;
  public static void main(String[] ignored) {
    zero = new float[65536];
    one = new int[65536]; one[65535] = 5;
    many = new double[65536]; many[0] = 1.25d; many[32768] = -2.5d; many[65535] = 3.75d;
    small = new float[] { -0.0f, 1.0f };
    dense = new float[] { 1.0f, 2.0f, 3.0f, 4.0f };
    references = new Object[1024]; references[511] = new Object();
    if (zero[65535] != 0.0f || one[65535] != 5 || many[0] != 1.25d
        || many[32768] != -2.5d || many[65535] != 3.75d || small[1] != 1.0f
        || dense[3] != 4.0f || references[510] != null || references[511] == null) throw new Error();
    result = 7;
  }
}
""",
}, ["SparseArrayMain.class"], "SparseArrayMain")

# Exact strict packed-vs-sparse crossover: at N=341 the packed payload ties
# old sparse and must keep sparse MR01; N=342 is a strict packed win.
build("array-savings-boundary", {
    "ArraySavingsBoundaryMain.java": """public final class ArraySavingsBoundaryMain {
  static int result;
  static float[] sparseTie, packedWin;
  public static void main(String[] ignored) {
    sparseTie = new float[1024]; packedWin = new float[1024];
    for (int i = 0; i < 342; i++) { packedWin[i] = 1.0f; if (i < 341) sparseTie[i] = 2.0f; }
    if (sparseTie[340] != 2.0f || sparseTie[341] != 0.0f
        || packedWin[340] != 1.0f || packedWin[341] != 1.0f) throw new Error();
    result = 7;
  }
}
""",
}, ["ArraySavingsBoundaryMain.class"], "ArraySavingsBoundaryMain")

# Mutate one generated CONSTANT_Float payload to a quiet-NaN payload. The Java8
# host oracle runs against the same patched data class; only the guest main/data
# classes enter the fixture ZIP, so no expected output enters execution.
def packed_nan_payload(name, data):
    if name != "PackedFloatData.class": return data
    mutable = bytearray(data)
    cp_count = int.from_bytes(mutable[8:10], "big")
    offset = 10; matches = 0; index = 1
    while index < cp_count:
        tag = mutable[offset]; offset += 1
        if tag == 4:
            if int.from_bytes(mutable[offset:offset + 4], "big") == 0x3fa00000:
                mutable[offset:offset + 4] = (0x7fc12345).to_bytes(4, "big"); matches += 1
            offset += 4
        elif tag == 1:
            length = int.from_bytes(mutable[offset:offset + 2], "big"); offset += 2 + length
        elif tag in (3, 9, 10, 11, 12, 17, 18): offset += 4
        elif tag in (5, 6): offset += 8; index += 1
        elif tag in (7, 8, 16, 19, 20): offset += 2
        elif tag == 15: offset += 3
        else: raise AssertionError((name, tag, offset))
        index += 1
    assert matches == 1, matches
    return bytes(mutable)

packed_assignments = "\n".join(
    "    values[%d] = %s;" % (i, "1.25f" if i % 2 == 0 else "-2.5f")
    for i in range(342))
build("packed-array-oracle", {
    "PackedFloatData.java": """final class PackedFloatData { static float[] make() {
    float[] values = new float[1024];
""" + packed_assignments + """
    values[500] = -0.0f; values[501] = Float.POSITIVE_INFINITY;
    values[502] = Float.NEGATIVE_INFINITY; values[503] = Float.MIN_VALUE;
    values[504] = -Float.MIN_VALUE; values[505] = Float.MAX_VALUE;
    return values;
} }
""",
    "PackedFloatMain.java": """public final class PackedFloatMain {
  static int result; static float[] values;
  public static void main(String[] ignored) { values = PackedFloatData.make();
    if (values.length != 1024) throw new Error(); result = 7; }
}
""",
    "PackedFloatOracle.java": """public final class PackedFloatOracle {
  public static void main(String[] ignored) {
    for (float value : PackedFloatData.make())
      System.out.printf(\"%08x%n\", Float.floatToRawIntBits(value));
  }
}
""",
}, ["PackedFloatMain.class", "PackedFloatData.class"], "PackedFloatOracle", mutate=packed_nan_payload)

# The only new profile behavior is ordinary allocation through the exact public
# no-arg constructor and Java assignability to the pinned Serializable interface.
# No host oracle is run: standard Random seeding depends on host time, which this
# intentionally state-free construction-only guest profile does not emulate.
build("random-construction", {
    "RandomConstructionMain.java": """import java.io.Serializable; import java.util.Random;
public final class RandomConstructionMain { static int result; public static void main(String[] ignored) {
  Random first = new Random(), second = new Random();
  if (first == second || !(first instanceof Serializable) || !(second instanceof Serializable)) throw new Error();
  result = 7;
} }
""",
}, ["RandomConstructionMain.class"])

# Standard Java 8 declarations let these classes compile; guest resolution must
# refuse both absent Random methods after the constructor has genuinely run.
build("random-next-int-omitted", {
    "RandomNextIntOmittedMain.java": """import java.util.Random;
public final class RandomNextIntOmittedMain { public static void main(String[] ignored) {
  Random random = new Random(); random.nextInt();
} }
""",
}, ["RandomNextIntOmittedMain.class"])
build("random-set-seed-omitted", {
    "RandomSetSeedOmittedMain.java": """import java.util.Random;
public final class RandomSetSeedOmittedMain { public static void main(String[] ignored) {
  Random random = new Random(); random.setSeed(1L);
} }
""",
}, ["RandomSetSeedOmittedMain.class"])

# This raw class is byte-for-byte the exact accepted bootstrap image. It must
# still be rejected as a raw platform replacement rather than becoming authority.
build("raw-random-replacement", {
    "RawRandomReplacementMain.java": """import java.util.Random;
public final class RawRandomReplacementMain { public static void main(String[] ignored) { new Random(); } }
""",
    "java/util/Random.java": """package java.util; import java.io.Serializable;
public class Random implements Serializable { public Random() { super(); } }
""",
}, ["RawRandomReplacementMain.class", "java/util/Random.class"])

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
    row = {"entries": entries, "bindingCount": count, "bootstrapCount": 97, "totalClassBytes": total,
           "classBytes": {name: (classes / name).stat().st_size for name in entries},
           "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
           "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(), "java8HostOracle": target is None, "selectedResource": None}
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n"); rows[label] = row

count_fixture("count-71", 71)
count_fixture("count-72", 72)
count_fixture("count-71-471911", 71, 471911)
count_fixture("count-71-471912", 71, 471912)

(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 97, "rawLimits": [71, 471911], "fixtures": rows,
    "scope": "generated Java-8 Math.cos bounded Q120 raw witnesses, retained asin/sin/sqrt and packed-float/sparse controls, malformed and atomic refusal vectors, raw71 capacity; no original/JAR/resource/network/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
