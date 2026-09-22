#!/usr/bin/env python3
"""Generate only trusted Java-8 Map.Entry fixtures.

No original artifact, JAR, precompiled class input, resource, network, or world is
opened.  The host JVM is used solely as the permitted oracle for these generated
sources; the EVM still resolves and executes their raw classfiles.
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-map-entry-link-fixtures-") and not out.exists()
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
        if mutate is not None:
            data = mutate(name, data)
        payloads[name] = data
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
        "java8HostOracle": host_main is not None,
        "selectedResource": None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row
    return row


# The generated implementation invokes every core Map.Entry declaration through
# the interface owner.  It proves assignment/cast assignability and getKey,
# getValue, setValue, equals, and hashCode dispatch without comparator helpers.
build("map-entry-dispatch", {
    "MapEntryDispatchMain.java": """import java.util.Map;
public final class MapEntryDispatchMain {
  static int result;
  static final class EntryImpl implements Map.Entry<Object,Object> {
    private final Object key;
    private Object value;
    EntryImpl(Object k, Object v) { key = k; value = v; }
    public Object getKey() { return key; }
    public Object getValue() { return value; }
    public Object setValue(Object next) { Object old = value; value = next; return old; }
    public boolean equals(Object other) {
      if (!(other instanceof Map.Entry)) return false;
      Map.Entry candidate = (Map.Entry) other;
      return candidate.getKey() == key && candidate.getValue() == value;
    }
    public int hashCode() { return 37; }
  }
  public static void main(String[] ignored) {
    Object key = new Object(); Object value = new Object(); Object replacement = new Object();
    Map.Entry<Object,Object> entry = new EntryImpl(key, value);
    if (entry.getKey() != key || entry.getValue() != value) throw new Error();
    if (entry.setValue(replacement) != value || entry.getValue() != replacement) throw new Error();
    if (!entry.equals(entry) || entry.hashCode() != 37) throw new Error();
    Object asObject = entry;
    if (!(asObject instanceof Map.Entry) || (Map.Entry) asObject != entry) throw new Error();
    result = 7;
  }
}
""",
}, ["MapEntryDispatchMain.class", "MapEntryDispatchMain$EntryImpl.class"], "MapEntryDispatchMain")

# Linking a null cast must resolve the nested name without active initialization
# or construction; it provides a minimal type-link/reopen witness.
build("map-entry-null-link", {
    "MapEntryNullLinkMain.java": """import java.util.Map;
public final class MapEntryNullLinkMain {
  static Map.Entry<Object,Object> saved;
  static int result;
  public static void main(String[] ignored) {
    Map.Entry<Object,Object> local = (Map.Entry<Object,Object>) null;
    if (local != null) throw new Error();
    saved = local;
    if (saved != null) throw new Error();
    result = 7;
  }
}
""",
}, ["MapEntryNullLinkMain.class"], "MapEntryNullLinkMain")

# The retained Map image still drives ordinary ConcurrentHashMap interface
# dispatch; this is intentionally unrelated to Map.Entry implementation state.
build("retained-map", {
    "RetainedMapMain.java": """import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
public final class RetainedMapMain {
  static int result;
  public static void main(String[] ignored) {
    Map<Object,Object> map = new ConcurrentHashMap<Object,Object>();
    Object key = new Object(); Object first = new Object(); Object second = new Object();
    if (map.put(key, first) != null || map.get(key) != first || !map.containsKey(key)) throw new Error();
    if (map.put(key, second) != first || map.get(key) != second || map.size() != 1) throw new Error();
    map.clear(); if (!map.isEmpty() || map.get(key) != null) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedMapMain.class"], "RetainedMapMain")

# Integer slot70 remains byte-for-byte pinned; its existing highestOneBit method
# is a compact retained executable witness independent of the new nested image.
build("retained-integer", {
    "RetainedIntegerMain.java": """public final class RetainedIntegerMain {
  static int result;
  public static void main(String[] ignored) {
    if (Integer.highestOneBit(0) != 0 || Integer.highestOneBit(1) != 1) throw new Error();
    if (Integer.highestOneBit(0x7fffffff) != 0x40000000) throw new Error();
    if (Integer.highestOneBit(-1) != 0x80000000) throw new Error();
    result = 7;
  }
}
""",
}, ["RetainedIntegerMain.class"], "RetainedIntegerMain")

# Java 8 comparator helpers are deliberately outside this exact five-method
# image.  Resolution must refuse before guest execution rather than link a host
# Comparator, lambda, default method, or synthetic implementation.
build("map-entry-comparator-omitted", {
    "MapEntryComparatorOmittedMain.java": """import java.util.Map;
public final class MapEntryComparatorOmittedMain {
  public static void main(String[] ignored) { Map.Entry.comparingByKey(); }
}
""",
}, ["MapEntryComparatorOmittedMain.class"])

# Bootstrap ownership rejects a valid raw same-name replacement before guest
# execution.  The only compiled Map.class is intentionally omitted from the ZIP.
map_source = """package java.util;
public interface Map<K,V> {
  public static interface Entry<K,V> {
    K getKey(); V getValue(); V setValue(V value); boolean equals(Object o); int hashCode();
  }
}
"""
build("raw-map-entry-replacement", {
    "RawMapEntryReplacementMain.java": "public final class RawMapEntryReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/Map.java": map_source,
}, ["RawMapEntryReplacementMain.class", "java/util/Map$Entry.class"])

# Malformed raw bytes are generated by a single magic-byte mutation of trusted
# local Java-8 output. They are never a precompiled external input.
def break_magic(name, data):
    assert name == "MalformedMapEntryMain.class" and data[:4] == b"\xca\xfe\xba\xbe"
    return b"\x00" + data[1:]
build("malformed-map-entry", {
    "MalformedMapEntryMain.java": "public final class MalformedMapEntryMain { public static void main(String[] ignored) {} }\n",
}, ["MalformedMapEntryMain.class"], mutate=break_magic)

(out / "summary.json").write_text(json.dumps({
    "generatedOnly": True, "bootstrapCount": 95, "rawLimits": [65, 381732],
    "fixtures": rows,
    "scope": "generated Java-8 Map.Entry link/interface-dispatch, retained Map/Integer, and refusal inputs only; no original/JAR/resource/world",
}, indent=2) + "\n")
print(json.dumps({"fixtures": list(rows), "count": len(rows)}, indent=2))
