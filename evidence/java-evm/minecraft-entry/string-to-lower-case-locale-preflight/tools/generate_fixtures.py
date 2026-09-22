#!/usr/bin/env python3
"""Generate only trusted Java-8 lower-case Locale.ROOT and retained fixtures.

The host JVM is an oracle for generated positive Java sources only. It never
loads an original class/JAR/resource and never supplies an EVM result.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-string-lower-locale-fixtures-") and not out.exists()
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

(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [69, 449904], "fixtures": rows,
    "scope": "generated Java-8 lower-case Locale.ROOT, refusal, and retained controls only; no original/JAR/resource/network/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
