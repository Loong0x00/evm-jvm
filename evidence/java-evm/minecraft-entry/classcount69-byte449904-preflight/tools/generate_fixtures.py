#!/usr/bin/env python3
"""Create only trusted generated Java-8 fixtures for raw69 / byte449904 capacity."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

out = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[5]
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-classcount69-byte449904-fixtures-") and not out.exists()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
out.mkdir()
sources_root = out / "src"; classes_root = out / "classes"
sources_root.mkdir(); classes_root.mkdir()
rows = {}


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
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": 95,
        "totalClassBytes": sum(len(data) for data in payloads.values()),
        "classBytes": {name: len(data) for name, data in payloads.items()},
        "classSHA256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None, "selectedResource": None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row
    return row


# Each code-point witness is independently host-oracled. Unit values are given
# as numeric char constants so NUL and unpaired surrogate source handling never
# depends on the host editor or source-file encoding.
def index_of(label, units, ch, expected):
    rendered = ", ".join("(char)0x%04x" % unit for unit in units)
    build(label, {
        "StringIndexOfMain.java": """public final class StringIndexOfMain {
  static int result;
  public static void main(String[] ignored) {
    String receiver = new String(new char[] { %s });
    int ch = %d;
    if (receiver.indexOf(ch) != %d) throw new Error();
    result = 7;
  }
}
""" % (rendered, ch, expected),
    }, ["StringIndexOfMain.class"], "StringIndexOfMain")


index_of("index-empty", [], 0x61, -1)
index_of("index-ascii-first", [0x61, 0x62, 0x63], 0x61, 0)
index_of("index-ascii-repeated", [0x61, 0x62, 0x63, 0x61], 0x61, 0)
index_of("index-ascii-absent", [0x61, 0x62, 0x63], 0x7a, -1)
index_of("index-nul", [0x61, 0, 0x62, 0], 0, 1)
index_of("index-bmp", [0x61, 0x03a9, 0x62], 0x03a9, 1)
index_of("index-raw-surrogate", [0x61, 0xd800, 0x62], 0xd800, 1)
index_of("index-supplementary", [0x61, 0xd83d, 0xde00, 0x62, 0xd83d, 0xde00], 0x1f600, 1)
index_of("index-negative", [0xffff], -1, -1)
index_of("index-out-of-range", [0xd83d, 0xde00], 0x110000, -1)

# The no-from-index overload is intentionally omitted from the owned image.
build("index-overload-omitted", {
    "StringIndexOfOverloadMain.java": """public final class StringIndexOfOverloadMain {
  public static void main(String[] ignored) {
    if ("abc".indexOf((int) 'a', 1) != -1) throw new Error();
  }
}
""",
}, ["StringIndexOfOverloadMain.class"])

# A main String[] signature does not initialize the owned String bootstrap.
build("string-uninitialized", {
    "StringUninitializedMain.java": """public final class StringUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["StringUninitializedMain.class"], "StringUninitializedMain")

# Bootstrap ownership rejects a valid same-name raw replacement before parsing
# guest execution. The replacement is compiled locally, never supplied input.
build("raw-string-replacement", {
    "RawStringReplacementMain.java": "public final class RawStringReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/String.java": "package java.lang; public final class String { public String() {} }\n",
}, ["RawStringReplacementMain.class", "java/lang/String.class"])

# Retain all already available executable String operations except deliberately
# deferred subSequence. This exercises constructors, natives, and the older
# ordinary Code methods independently of the new indexOf(int) invocation.
build("retained-string", {
    "RetainedStringMain.java": """public final class RetainedStringMain {
  static int result;
  public static void main(String[] ignored) {
    String owned = new String(new char[] { 'a', 'B', '-', 'c' });
    String copy = new String(owned);
    if (owned.length() != 4 || owned.isEmpty() || owned.charAt(1) != 'B') throw new Error();
    if (!owned.equals(copy) || owned.hashCode() != copy.hashCode() || owned.toString() != owned) throw new Error();
    if (owned.compareTo("aB-d") >= 0 || owned.intern() != owned) throw new Error();
    if (!owned.substring(1).equals("B-c") || owned.lastIndexOf("B") != 1) throw new Error();
    if (!owned.startsWith("aB") || !owned.equalsIgnoreCase("Ab-C")) throw new Error();
    String[] split = "a-b.".split("-|\\\\.");
    if (split.length != 2 || !split[0].equals("a") || !split[1].equals("b")) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedStringMain.class"], "RetainedStringMain")

# Retained Map.Entry and Integer roots remain executable after the changed root.
build("map-entry-dispatch", {
    "MapEntryDispatchMain.java": """import java.util.Map;
public final class MapEntryDispatchMain {
  static int result;
  static final class EntryImpl implements Map.Entry<Object,Object> {
    private final Object key; private Object value;
    EntryImpl(Object k, Object v) { key = k; value = v; }
    public Object getKey() { return key; } public Object getValue() { return value; }
    public Object setValue(Object next) { Object old = value; value = next; return old; }
    public boolean equals(Object other) { if (!(other instanceof Map.Entry)) return false; Map.Entry e = (Map.Entry) other; return e.getKey() == key && e.getValue() == value; }
    public int hashCode() { return 37; }
  }
  public static void main(String[] ignored) {
    Object key = new Object(), value = new Object(), replacement = new Object();
    Map.Entry<Object,Object> entry = new EntryImpl(key, value);
    if (entry.getKey() != key || entry.getValue() != value || entry.setValue(replacement) != value || entry.getValue() != replacement || !entry.equals(entry) || entry.hashCode() != 37) throw new Error();
    result = 7;
  }
}
""",
}, ["MapEntryDispatchMain.class", "MapEntryDispatchMain$EntryImpl.class"], "MapEntryDispatchMain")
build("map-entry-null-link", {
    "MapEntryNullLinkMain.java": """import java.util.Map;
public final class MapEntryNullLinkMain { static int result; public static void main(String[] ignored) { Map.Entry<Object,Object> value = (Map.Entry<Object,Object>) null; if (value != null) throw new Error(); result = 7; } }
""",
}, ["MapEntryNullLinkMain.class"], "MapEntryNullLinkMain")
build("retained-map", {
    "RetainedMapMain.java": """import java.util.Map; import java.util.concurrent.ConcurrentHashMap;
public final class RetainedMapMain { static int result; public static void main(String[] ignored) { Map<Object,Object> map = new ConcurrentHashMap<Object,Object>(); Object key = new Object(), first = new Object(), second = new Object(); if (map.put(key, first) != null || map.get(key) != first || !map.containsKey(key) || map.put(key, second) != first || map.get(key) != second || map.size() != 1) throw new Error(); map.clear(); if (!map.isEmpty()) throw new Error(); result = 7; } }
""",
}, ["RetainedMapMain.class"], "RetainedMapMain")
build("retained-integer", {
    "RetainedIntegerMain.java": """public final class RetainedIntegerMain { static int result; public static void main(String[] ignored) { if (Integer.highestOneBit(0) != 0 || Integer.highestOneBit(0x7fffffff) != 0x40000000 || Integer.highestOneBit(-1) != 0x80000000) throw new Error(); result = 7; } }
""",
}, ["RetainedIntegerMain.class"], "RetainedIntegerMain")
build("map-entry-comparator-omitted", {
    "MapEntryComparatorOmittedMain.java": "import java.util.Map; public final class MapEntryComparatorOmittedMain { public static void main(String[] ignored) { Map.Entry.comparingByKey(); } }\n",
}, ["MapEntryComparatorOmittedMain.class"])
map_source = """package java.util; public interface Map<K,V> { public static interface Entry<K,V> { K getKey(); V getValue(); V setValue(V value); boolean equals(Object o); int hashCode(); } }\n"""
build("raw-map-entry-replacement", {
    "RawMapEntryReplacementMain.java": "public final class RawMapEntryReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/Map.java": map_source,
}, ["RawMapEntryReplacementMain.class", "java/util/Map$Entry.class"])
def break_magic(name, data):
    assert name == "MalformedMapEntryMain.class" and data[:4] == b"\xca\xfe\xba\xbe"
    return b"\x00" + data[1:]
build("malformed-map-entry", {
    "MalformedMapEntryMain.java": "public final class MalformedMapEntryMain { public static void main(String[] ignored) {} }\n",
}, ["MalformedMapEntryMain.class"], mutate=break_magic)

# Retain String/Map/Integer controls and cover raw69 aggregate-byte frontiers. The eight padding locations
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
    src = sources_root / label; classes = classes_root / label
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
    row = {"entries": entries, "bindingCount": count, "bootstrapCount": 95, "totalClassBytes": total,
           "classBytes": {name: (classes / name).stat().st_size for name in entries},
           "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
           "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(), "java8HostOracle": target is None, "selectedResource": None}
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n"); rows[label] = row

count_fixture("count-69", 69)
count_fixture("count-70", 70)
count_fixture("count-69-449904", 69, 449904)
count_fixture("count-69-449905", 69, 449905)
(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 95, "rawLimits": [69, 449904], "fixtures": rows,
    "scope": "generated Java-8 String/Map/Integer retained controls and raw69 capacity inputs only; no original/JAR/external class/resource/network/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
