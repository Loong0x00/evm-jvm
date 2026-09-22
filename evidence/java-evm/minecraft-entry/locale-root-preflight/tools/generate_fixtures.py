#!/usr/bin/env python3
"""Generate only trusted Java-8 Locale.ROOT and retained fixtures."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-locale-root-fixtures-") and not out.exists()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
out.mkdir(); sources_root = out / "src"; classes_root = out / "classes"
sources_root.mkdir(); classes_root.mkdir(); rows = {}


def build(label, sources, entries, host_main=None, mutate=None):
    src = sources_root / label; classes = classes_root / label
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


# ROOT is referenced twice through the field owner. The generated Java-8 oracle
# proves the singleton/non-null identity claim; EVM executes the unchanged bytes.
build("locale-root", {
    "LocaleRootMain.java": """import java.util.Locale;
public final class LocaleRootMain {
  static int result;
  public static void main(String[] ignored) {
    Locale first = Locale.ROOT;
    Locale second = Locale.ROOT;
    if (first == null || second == null || first != second) throw new Error();
    if (!(first instanceof Locale) || (Locale) (Object) first != second) throw new Error();
    result = 7;
  }
}
""",
}, ["LocaleRootMain.class"], "LocaleRootMain")

# A class literal resolves the owned type but must not fabricate/trigger ROOT
# initialization. The gate inspects only transport metadata after EVM execution.
build("locale-class-literal-uninitialized", {
    "LocaleLiteralMain.java": """import java.util.Locale;
public final class LocaleLiteralMain {
  static int result;
  public static void main(String[] ignored) {
    Class<?> type = Locale.class;
    if (type == null) throw new Error();
    result = 7;
  }
}
""",
}, ["LocaleLiteralMain.class"], "LocaleLiteralMain")

# Retained String, Map.Entry, and Integer witnesses remain independent ordinary
# guest executions after image96. Their source uses no Locale API.
build("retained-string", {
    "RetainedStringMain.java": """public final class RetainedStringMain {
  static int result;
  public static void main(String[] ignored) {
    String owned = new String(new char[] { 'a', 'B', '-', 'c' });
    String copy = new String(owned);
    if (owned.length() != 4 || !owned.equals(copy) || owned.indexOf('B') != 1) throw new Error();
    if (!owned.substring(1).equals("B-c") || owned.intern() != owned) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedStringMain.class"], "RetainedStringMain")
build("retained-map", {
    "RetainedMapMain.java": """import java.util.Map; import java.util.concurrent.ConcurrentHashMap;
public final class RetainedMapMain {
  static int result;
  public static void main(String[] ignored) {
    Map<Object,Object> map = new ConcurrentHashMap<Object,Object>();
    Object key = new Object(), first = new Object(), second = new Object();
    if (map.put(key, first) != null || map.get(key) != first || map.put(key, second) != first) throw new Error();
    if (map.get(key) != second || map.size() != 1) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedMapMain.class"], "RetainedMapMain")
build("retained-integer", {
    "RetainedIntegerMain.java": """public final class RetainedIntegerMain {
  static int result;
  public static void main(String[] ignored) {
    if (Integer.highestOneBit(0) != 0 || Integer.highestOneBit(0x7fffffff) != 0x40000000) throw new Error();
    if (Integer.highestOneBit(-1) != 0x80000000) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedIntegerMain.class"], "RetainedIntegerMain")

# getDefault is outside image96. It is a generated member-resolution refusal,
# never a host locale/default fallback.
build("locale-default-omitted", {
    "LocaleDefaultOmittedMain.java": """import java.util.Locale;
public final class LocaleDefaultOmittedMain {
  public static void main(String[] ignored) { if (Locale.getDefault() == null) throw new Error(); }
}
""",
}, ["LocaleDefaultOmittedMain.class"])

locale_source = """package java.util;
import java.io.Serializable;
public final class Locale implements Cloneable, Serializable {
  public static final Locale ROOT;
  private Locale() {}
  static { ROOT = new Locale(); }
}
"""
build("raw-locale-replacement", {
    "RawLocaleReplacementMain.java": "public final class RawLocaleReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/Locale.java": locale_source,
}, ["RawLocaleReplacementMain.class", "java/util/Locale.class"])


def break_magic(name, data):
    assert name == "MalformedLocaleMain.class" and data[:4] == b"\xca\xfe\xba\xbe"
    return b"\x00" + data[1:]


build("malformed-locale", {
    "MalformedLocaleMain.java": "public final class MalformedLocaleMain { public static void main(String[] ignored) {} }\n",
}, ["MalformedLocaleMain.class"], mutate=break_magic)

(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 96, "rawLimits": [69, 449904], "fixtures": rows,
    "scope": "generated Java-8 Locale ROOT, retained String/Map/Integer, and refusal inputs only; no original/JAR/resource/network/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
