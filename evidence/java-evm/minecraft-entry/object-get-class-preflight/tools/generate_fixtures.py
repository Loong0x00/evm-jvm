#!/usr/bin/env python3
"""Create only trusted generated Java-8 fixtures for raw cap32 and retained gates.

No original artifact, class, resource, or world is read. Host execution is limited
strictly to generated positive/control sources and is not an EVM execution path.
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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-object-get-class-fixtures-")
assert not out.exists()
out.mkdir()
source_root = out / "src"
classes_root = out / "classes"
source_root.mkdir()
classes_root.mkdir()
javac = Path("/usr/lib/jvm/java-8-openjdk/bin/javac")
java = Path("/usr/lib/jvm/java-8-openjdk/bin/java")
assert javac.is_file() and java.is_file()
rows = {}

def build(label, sources, entries, host_main=None):
    src = source_root / label
    classes = classes_root / label
    src.mkdir()
    classes.mkdir()
    for name, text in sources.items():
        path = src / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                    *map(str, sorted(src.rglob("*.java")))], check=True)
    if host_main is not None:
        subprocess.run([java, "-cp", classes, host_main], check=True)
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for name in entries:
            data = (classes / name).read_bytes()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)
    row = {
        "entries": entries, "bindingCount": len(entries),
        "totalClassBytes": sum((classes / name).stat().st_size for name in entries),
        "classBytes": {name: (classes / name).stat().st_size for name in entries},
        "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
        "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "java8HostOracle": host_main is not None,
    }
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row
    return row

build("system-err", {
    "SystemErrProbe.java": """public final class SystemErrProbe {
  static int result;
  static final class Handoff {
    final java.io.PrintStream value;
    Handoff(java.io.PrintStream input) { value = input; }
  }
  public static void main(String[] ignored) {
    java.io.PrintStream first = System.err;
    java.io.PrintStream second = System.err;
    if (first == null || first != second) throw new Error();
    Handoff handoff = new Handoff(first);
    if (handoff.value != second) throw new Error();
    result = 7;
  }
}
""",
}, ["SystemErrProbe.class", "SystemErrProbe$Handoff.class"], "SystemErrProbe")

# Positive surface: each append returns the same guest object, preserves order,
# and toString constructs independent guest String copies through String(char[]).
build("stringbuilder", {
    "StringBuilderMain.java": """public final class StringBuilderMain {
  static int result;
  public static void main(String[] ignored) {
    StringBuilder builder = new StringBuilder();
    String empty = builder.toString();
    if (!empty.equals("") || empty == "") throw new Error();
    if (builder.append("ab") != builder) throw new Error();
    if (builder.append("C") != builder) throw new Error();
    String first = builder.toString();
    if (!first.equals("abC") || first == "abC") throw new Error();
    if (builder.append("d") != builder) throw new Error();
    String second = builder.toString();
    if (!second.equals("abCd") || first == second || !first.equals("abC")) throw new Error();
    result = 7;
  }
}
""",
}, ["StringBuilderMain.class"], "StringBuilderMain")

# The deliberately bounded append(String) profile does not expose Java 8's
# append-null-to-literal extension.  Its first input.length dereference yields
# a catchable guest NPE before any destination allocation.
build("stringbuilder-null", {
    "StringBuilderNullMain.java": """public final class StringBuilderNullMain {
  static int result;
  public static void main(String[] ignored) {
    try { new StringBuilder().append((String) null); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["StringBuilderNullMain.class"])

# No StringBuilder bytecode is resolved on this root; its bootstrap class must
# remain absent from initialization state.
build("stringbuilder-uninitialized", {
    "StringBuilderUninitializedMain.java": """public final class StringBuilderUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["StringBuilderUninitializedMain.class"], "StringBuilderUninitializedMain")

# This generated-only quota control reaches the bounded array-elements limit
# through a real append.  The second append must OOM before copying, then be
# caught by guest code.  It intentionally has no host oracle: host Java's
# general-purpose StringBuilder allocation policy is outside this profile.
build("stringbuilder-oom", {
    "StringBuilderOOMMain.java": """public final class StringBuilderOOMMain {
  static int result;
  public static void main(String[] ignored) {
    String input = new String(new char[65536]);
    StringBuilder builder = new StringBuilder();
    builder.append(input);
    try { builder.append(input); throw new Error(); }
    catch (OutOfMemoryError expected) { result = 7; }
  }
}
""",
}, ["StringBuilderOOMMain.class"])

build("raw-stringbuilder", {
    "RawStringBuilderReplacementMain.java": "public final class RawStringBuilderReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/StringBuilder.java": "package java.lang; public final class StringBuilder { public StringBuilder() {} }\n",
}, ["RawStringBuilderReplacementMain.class", "java/lang/StringBuilder.class"])

# TreeMap is deliberately an Object-only constructor image. This positive probe
# proves real guest allocation, non-null results, and stable object identity; it
# does not call Map, SortedMap, ordering, or mutation APIs.
build("treemap", {
    "TreeMapConstructorMain.java": """import java.util.TreeMap;
public final class TreeMapConstructorMain {
  static TreeMap stable;
  static int result;
  public static void main(String[] ignored) {
    TreeMap first = new TreeMap();
    TreeMap second = new TreeMap();
    if (first == null || second == null || first == second) throw new Error();
    stable = first;
    if (stable != first || stable == second) throw new Error();
    result = 7;
  }
}
""",
}, ["TreeMapConstructorMain.class"], "TreeMapConstructorMain")

# This root has no TreeMap symbol use; the appended image must not initialize.
build("treemap-uninitialized", {
    "TreeMapUninitializedMain.java": """public final class TreeMapUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["TreeMapUninitializedMain.class"], "TreeMapUninitializedMain")

# Bootstrap ownership prevents a raw bundle from substituting TreeMap.
build("raw-treemap", {
    "RawTreeMapReplacementMain.java": "public final class RawTreeMapReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/TreeMap.java": "package java.util; public final class TreeMap { public TreeMap() {} }\n",
}, ["RawTreeMapReplacementMain.class", "java/util/TreeMap.class"])

# The Java 8 compiler resolves this as TreeMap.put. The bounded image has no
# mutation method, so the EVM must expose an honest profile refusal rather than
# fabricate a Map result.
build("treemap-mutation-omitted", {
    "TreeMapMutationOmittedMain.java": """import java.util.TreeMap;
public final class TreeMapMutationOmittedMain {
  public static void main(String[] ignored) {
    TreeMap map = new TreeMap();
    map.put("key", "value");
  }
}
""",
}, ["TreeMapMutationOmittedMain.class"])

# This separately names the absent SortedMap interface and invokes its mutation
# slot after ordinary TreeMap construction. It must report the missing interface,
# not claim TreeMap implements it.
build("treemap-sortedmap-omitted", {
    "TreeMapSortedMapOmittedMain.java": """import java.util.SortedMap;
import java.util.TreeMap;
public final class TreeMapSortedMapOmittedMain {
  public static void main(String[] ignored) {
    SortedMap map = new TreeMap();
    map.put("key", "value");
  }
}
""",
}, ["TreeMapSortedMapOmittedMain.class"])

build("system-uninitialized", {
    "SystemUninitializedProbe.java": """public final class SystemUninitializedProbe {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["SystemUninitializedProbe.class"], "SystemUninitializedProbe")

build("failed-init", {
    "FailedInitProbe.java": """public final class FailedInitProbe {
  static int result;
  public static void main(String[] ignored) {
    try { Broken.touch(); } catch (ExceptionInInitializerError expected) { result += 1; }
    try { Broken.touch(); } catch (NoClassDefFoundError expected) { result += 2; }
    if (result != 3) throw new Error();
  }
}
""",
    "Broken.java": """final class Broken {
  static int boom = 1 / 0;
  static void touch() {}
}
""",
}, ["FailedInitProbe.class", "Broken.class"], "FailedInitProbe")

build("raw-system", {
    "RawSystemReplacementMain.java": "public final class RawSystemReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/System.java": "package java.lang; public final class System {}\n",
}, ["RawSystemReplacementMain.class", "java/lang/System.class"])
build("raw-printstream", {
    "RawPrintStreamReplacementMain.java": "public final class RawPrintStreamReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/io/PrintStream.java": "package java.io; public class PrintStream { public PrintStream() {} }\n",
}, ["RawPrintStreamReplacementMain.class", "java/io/PrintStream.class"])

# lastIndexOf(String) cases are kept separate so every required result has its
# own q1/q7/direct/reopen receipt chain. Java source literals are expressed as
# UTF-16 units, including a surrogate-pair witness.
def java_literal(text):
    units = text.encode("utf-16-be")
    return '"' + ''.join("\\u%04x" % int.from_bytes(units[i:i + 2], "big") for i in range(0, len(units), 2)) + '"'

def last_index(label, receiver, target, expected):
    build(label, {
        "LastIndexOfMain.java": """public final class LastIndexOfMain {
  static int result;
  public static void main(String[] ignored) {
    String receiver = %s;
    String target = %s;
    if (receiver.lastIndexOf(target) != %d) throw new Error();
    result = 7;
  }
}
""" % (java_literal(receiver), java_literal(target), expected),
    }, ["LastIndexOfMain.class"], "LastIndexOfMain")

last_index("last-index-suffix", "abcabc", "abc", 3)
last_index("last-index-middle", "abc123abc", "123", 3)
last_index("last-index-prefix", "abcxyz", "abc", 0)
last_index("last-index-overlap", "aaaaa", "aaa", 2)
last_index("last-index-repeated", "bananana", "ana", 5)
last_index("last-index-absent", "abc", "z", -1)
last_index("last-index-empty-target", "abc", "", 3)
last_index("last-index-empty-receiver", "", "", 0)
last_index("last-index-longer-target", "ab", "abc", -1)
last_index("last-index-utf16", "xΩyΩ", "Ω", 3)
last_index("last-index-surrogate", "x😀y😀", "😀", 4)

# The first bytecode operation in the guest method is target.length(); null
# therefore follows the normal catchable interpreter NPE path without a host
# binding or a synthetic null branch.
build("last-index-null", {
    "LastIndexOfNullMain.java": """public final class LastIndexOfNullMain {
  static int result;
  public static void main(String[] ignored) {
    try { "x".lastIndexOf((String) null); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["LastIndexOfNullMain.class"], "LastIndexOfNullMain")

# A main signature alone must not initialize the String bootstrap image.
build("string-uninitialized", {
    "StringUninitializedMain.java": """public final class StringUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["StringUninitializedMain.class"], "StringUninitializedMain")

# String remains bootstrap-owned; raw substitution is rejected before parsing.
build("raw-string", {
    "RawStringReplacementMain.java": "public final class RawStringReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/String.java": "package java.lang; public final class String { public String() {} }\n",
}, ["RawStringReplacementMain.class", "java/lang/String.class"])

# Focused bounded lock surface: an interface receiver invokes the ordinary
# Java-8 lockInterruptibly signature repeatedly, then balances through the same
# existing hold counter via unlock. The host oracle only runs this trusted source.
build("lock-interruptibly", {
    "LockInterruptiblyMain.java": """import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
public final class LockInterruptiblyMain {
  static int result;
  public static void main(String[] ignored) throws InterruptedException {
    ReentrantLock concrete = new ReentrantLock();
    Lock lock = concrete;
    lock.lockInterruptibly();
    lock.lockInterruptibly();
    concrete.lockInterruptibly();
    lock.unlock();
    lock.unlock();
    concrete.unlock();
    result = 7;
  }
}
""",
}, ["LockInterruptiblyMain.class"], "LockInterruptiblyMain")

# The declared checked signature remains ordinary Java source. The null receiver
# reaches invokeinterface and must take the existing catchable guest NPE path;
# there is no interrupt-state observation or synthetic interrupt outcome.
build("lock-interruptibly-null", {
    "LockInterruptiblyNullMain.java": """import java.util.concurrent.locks.Lock;
public final class LockInterruptiblyNullMain {
  static int result;
  public static void main(String[] ignored) throws InterruptedException {
    Lock lock = null;
    try { lock.lockInterruptibly(); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["LockInterruptiblyNullMain.class"], "LockInterruptiblyNullMain")

# A root with no lock symbols proves neither replaced bootstrap image initializes.
build("lock-interruptibly-uninitialized", {
    "LockInterruptiblyUninitializedMain.java": """public final class LockInterruptiblyUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["LockInterruptiblyUninitializedMain.class"], "LockInterruptiblyUninitializedMain")

# Both replaced image names remain bootstrap-owned and reject raw replacement
# before parser execution or Head mutation.
build("raw-lock-interruptibly-lock", {
    "RawLockInterruptiblyLockReplacementMain.java": "public final class RawLockInterruptiblyLockReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/concurrent/locks/Lock.java": "package java.util.concurrent.locks; public interface Lock {}\n",
}, ["RawLockInterruptiblyLockReplacementMain.class", "java/util/concurrent/locks/Lock.class"])
build("raw-lock-interruptibly-reentrant", {
    "RawLockInterruptiblyReentrantReplacementMain.java": "public final class RawLockInterruptiblyReentrantReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/concurrent/locks/ReentrantLock.java": "package java.util.concurrent.locks; public class ReentrantLock { public ReentrantLock() {} }\n",
}, ["RawLockInterruptiblyReentrantReplacementMain.class", "java/util/concurrent/locks/ReentrantLock.class"])

# Retained EnumSet / real ACC_ENUM controls. FocusLevel has the compiler-issued
# ACC_ENUM bit; the recorded classfile flag is checked below without host parsing.
enum_positive = build("enumset", {
    "EnumSetMain.java": """import java.util.*;
public final class EnumSetMain {
  static int result;
  public static void main(String[] ignored) {
    EnumSet<FocusLevel> values = FocusLevel.ALL;
    if (values.size() != 3) throw new Error();
    Iterator<FocusLevel> it = values.iterator(); int packed = 0;
    while (it.hasNext()) packed = packed * 10 + it.next().ordinal();
    if (packed != 12 || it.hasNext()) throw new Error();
    try { it.next(); throw new Error(); } catch (NoSuchElementException expected) { result = 7; }
    if (result != 7) throw new Error();
  }
}
""",
    "FocusLevel.java": """import java.util.EnumSet;
enum FocusLevel { LOW, MID, HIGH; static final EnumSet<FocusLevel> ALL = EnumSet.allOf(FocusLevel.class); }
""",
}, ["EnumSetMain.class", "FocusLevel.class"], "EnumSetMain")
def class_access(data):
    assert data[:4] == b"\xca\xfe\xba\xbe"
    count = int.from_bytes(data[8:10], "big")
    at = 10
    index = 1
    while index < count:
        tag = data[at]; at += 1
        if tag == 1:
            width = int.from_bytes(data[at:at + 2], "big"); at += 2 + width
        elif tag in (3, 4): at += 4
        elif tag in (5, 6): at += 8; index += 1
        elif tag in (7, 8, 16): at += 2
        elif tag in (9, 10, 11, 12, 18): at += 4
        elif tag == 15: at += 3
        else: raise AssertionError((tag, index))
        index += 1
    return int.from_bytes(data[at:at + 2], "big")

focus = (classes_root / "enumset/FocusLevel.class").read_bytes()
focus_access = class_access(focus)
assert focus_access & 0x4000
rows["enumset"]["focusLevelAccessFlags"] = focus_access
(out / "enumset.json").write_text(json.dumps(rows["enumset"], indent=2) + "\n")

build("enumset-errors", {
    "EnumSetErrorMain.java": """import java.util.EnumSet;
public final class EnumSetErrorMain {
  static int result;
  public static void main(String[] ignored) {
    try { EnumSet.allOf(null); } catch (NullPointerException expected) { result += 1; }
    try { EnumSet.allOf((Class) String.class); } catch (ClassCastException expected) { result += 2; }
    if (result != 3) throw new Error();
  }
}
""",
}, ["EnumSetErrorMain.class"], "EnumSetErrorMain")
build("enumset-failed", {
    "FailedEnumMain.java": """import java.util.EnumSet;
public final class FailedEnumMain {
  static int result;
  public static void main(String[] ignored) {
    try { FailingLevel.touch(); } catch (ExceptionInInitializerError expected) { result += 1; }
    try { EnumSet.allOf(FailingLevel.class); } catch (NoClassDefFoundError expected) { result += 2; }
    if (result != 3) throw new Error();
  }
}
""",
    "FailingLevel.java": """enum FailingLevel { A, B; static int boom = fail();
  static int fail() { throw new RuntimeException(); } static void touch() {} }
""",
}, ["FailedEnumMain.class", "FailingLevel.class"], "FailedEnumMain")
build("enumset-uninitialized", {
    "EnumSetUninitializedMain.java": """import java.util.EnumSet;
public final class EnumSetUninitializedMain { public static void main(String[] ignored) { EnumSet.allOf(OtherLevel.class); } }
""",
    "OtherLevel.java": "enum OtherLevel { A, B }\n",
}, ["EnumSetUninitializedMain.class", "OtherLevel.class"])

# Object.getClass binding13: dynamic dispatch must return precisely the
# canonical Class mirror for the object's real subclass. This checks a class
# literal, repeated calls, and two distinct same-class instances, then repeats
# on the canonical Class mirror itself.
build("object-getclass", {
    "ObjectGetClassMain.java": """public final class ObjectGetClassMain {
  static int result;
  static class Parent {}
  static final class Child extends Parent {}
  public static void main(String[] ignored) {
    Child first = new Child(); Child second = new Child();
    Class<?> literal = Child.class;
    Class<?> one = first.getClass(); Class<?> two = first.getClass();
    Class<?> three = second.getClass();
    if (one != literal || one != two || one != three) throw new Error();
    if (one.getClass() != Class.class) throw new Error();
    result = 7;
  }
}
""",
}, ["ObjectGetClassMain.class", "ObjectGetClassMain$Parent.class", "ObjectGetClassMain$Child.class"], "ObjectGetClassMain")

# ldc supplies a canonical mirror but does not actively initialize Dormant.
# Its subsequent Object.getClass call may materialize Class.class's mirror, but
# must not run Dormant's failing <clinit>.
build("object-getclass-noinit", {
    "ObjectGetClassNoInitMain.java": """public final class ObjectGetClassNoInitMain {
  static int result;
  static final class Dormant { static int value = fail(); static int fail() { throw new Error(); } }
  public static void main(String[] ignored) {
    Class<?> dormant = Dormant.class;
    if (dormant.getClass() != Class.class) throw new Error();
    result = 7;
  }
}
""",
}, ["ObjectGetClassNoInitMain.class", "ObjectGetClassNoInitMain$Dormant.class"], "ObjectGetClassNoInitMain")

# A null invokevirtual is handled by the ordinary guest NPE path before the
# native is selected/executed.
build("object-getclass-null", {
    "ObjectGetClassNullMain.java": """public final class ObjectGetClassNullMain {
  static int result;
  public static void main(String[] ignored) {
    Object value = null;
    try { value.getClass(); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["ObjectGetClassNullMain.class"], "ObjectGetClassNullMain")

# No raw Object image is bundled. This array therefore resolves the bootstrap
# final native, then reaches the explicit array receiver refusal rather than a
# synthetic array mirror or host type query.
build("object-getclass-array", {
    "ObjectGetClassArrayMain.java": """public final class ObjectGetClassArrayMain {
  public static void main(String[] ignored) { Object value = new int[1]; value.getClass(); }
}
""",
}, ["ObjectGetClassArrayMain.class"], "ObjectGetClassArrayMain")

# Compile against a temporary Class shell but intentionally omit that shell from
# the archive. The EVM uses its owned Class constructor, producing an ordinary
# forged Class object. Object.getClass must reject it through canonical-mirror
# validation; no raw Class replacement is supplied.
build("object-getclass-forged-mirror", {
    "ObjectGetClassForgedMirrorMain.java": """public final class ObjectGetClassForgedMirrorMain {
  public static void main(String[] ignored) { Class<?> forged = new Class(); forged.getClass(); }
}
""",
    "java/lang/Class.java": "package java.lang; public class Class<T> { public Class() {} }\n",
}, ["ObjectGetClassForgedMirrorMain.class"])

# Primitive literals remain outside the Class-mirror profile before their
# receiver call; this must stay a refusal rather than inventing primitive
# mirrors.
build("object-getclass-primitive", {
    "ObjectGetClassPrimitiveMain.java": """public final class ObjectGetClassPrimitiveMain {
  public static void main(String[] ignored) { int.class.getClass(); }
}
""",
}, ["ObjectGetClassPrimitiveMain.class"], "ObjectGetClassPrimitiveMain")

# Supplying java/lang/Object remains supported only as an ordinary raw class.
# Its Code return is intentionally null: binding13 is bootstrap slot0 only and
# must not replace this user image merely because the declaration matches.
build("raw-object-getclass", {
    "RawObjectGetClassMain.java": """public final class RawObjectGetClassMain {
  static int result;
  public static void main(String[] ignored) {
    Object value = new Object(); if (value.getClass() != null) throw new Error(); result = 7;
  }
}
""",
    "java/lang/Object.java": """package java.lang;
public class Object { public Object() {} public final Class<?> getClass() { return null; } }
""",
}, ["RawObjectGetClassMain.class", "java/lang/Object.class"])

# The shared allocator's failure must be an ordinary catchable guest OOM with
# no partial loader/name/mirror publication. 1023 ordinary objects leave the
# final name+mirror reservation unavailable.
build("object-getclass-oom", {
    "ObjectGetClassOOMMain.java": """public final class ObjectGetClassOOMMain {
  static int result;
  public static void main(String[] ignored) {
    Object[] values = new Object[1023];
    for (int i = 0; i < values.length; ++i) values[i] = new Object();
    try { values[0].getClass(); throw new Error(); }
    catch (OutOfMemoryError expected) { result = 7; }
  }
}
""",
}, ["ObjectGetClassOOMMain.class"])

build("queue", {
    "QueueMain.java": """import java.util.Queue; import java.util.concurrent.ConcurrentLinkedQueue;
public final class QueueMain {
  static int result;
  public static void main(String[] ignored) {
    Queue<Object> queue = new ConcurrentLinkedQueue<Object>(); Object a = new Object(); Object b = new Object();
    if (!queue.add(a) || !queue.add(b) || queue.size() != 2 || queue.poll() != a || queue.poll() != b || queue.poll() != null) throw new Error();
    result = 7;
  }
}
""",
}, ["QueueMain.class"], "QueueMain")

wide_fields = "".join("  int f%d;\n" % i for i in range(1025))
build("oom", {
    "OOMNewInstanceMain.java": """public final class OOMNewInstanceMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    try { TooWideTarget.class.newInstance(); result = 1; }
    catch (OutOfMemoryError expected) { result = 7; }
    if (result != 7) throw new Error();
  }
}
""",
    "TooWideTarget.java": "public final class TooWideTarget {\n" + wide_fields + "  public TooWideTarget() {}\n}\n",
}, ["OOMNewInstanceMain.class", "TooWideTarget.class"])

# Exact raw32 and aggregate-byte boundaries retain the accepted generated gate.
def count_source(count, pads=()):
    tails = count - 1
    calls = " + ".join("Tail%02d.touch()" % i for i in range(1, tails + 1))
    fields = "".join("  private static final String PAD%02d = \"%s\";\n" % (i, value) for i, value in enumerate(pads))
    return """public final class CountMain {
%s  static int sentinel;
  public static void main(String[] ignored) {
    sentinel = %s;
    if (sentinel != %d) throw new Error();
  }
}
""" % (fields, calls, tails * (tails + 1) // 2)

def count_fixture(label, count, target=None):
    src = source_root / label
    classes = classes_root / label
    src.mkdir(); classes.mkdir()
    for i in range(1, count):
        (src / ("Tail%02d.java" % i)).write_text("final class Tail%02d { static int touch() { return %d; } }\n" % (i, i))
    def compile(pads=()):
        (src / "CountMain.java").write_text(count_source(count, pads))
        shutil.rmtree(classes); classes.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                        *map(str, sorted(src.glob("*.java")))], check=True)
        return sum(path.stat().st_size for path in classes.glob("*.class"))
    total = compile()
    pads = []
    if target is not None:
        assert total < target
        overhead = compile([""] * 5)
        need = target - total - (overhead - total)
        assert 0 <= need <= 5 * 65000
        pads = [(chr(65 + i) + "x" * (min(65000, need - i * 65000) - 1)) if need > i * 65000 else "" for i in range(5)]
        total = compile(pads)
        for _ in range(3):
            delta = target - total
            if delta == 0: break
            at = max(i for i, value in enumerate(pads) if value)
            assert 0 <= len(pads[at]) + delta <= 65000
            pads[at] = pads[at][:len(pads[at]) + delta] if delta < 0 else pads[at] + "x" * delta
            total = compile(pads)
        assert total == target, (label, total, target)
    if target is None:
        subprocess.run([java, "-cp", classes, "CountMain"], check=True)
    entries = ["CountMain.class"] + ["Tail%02d.class" % i for i in range(1, count)]
    archive = out / (label + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
        for name in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, (classes / name).read_bytes())
    row = {"entries": entries, "bindingCount": count, "totalClassBytes": total,
           "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
           "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(), "java8HostOracle": target is None}
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row

for count in (29, 30, 31, 32, 33): count_fixture("count-%d" % count, count)
count_fixture("count-32-262144", 32, 262144)
count_fixture("count-32-262145", 32, 262145)
(out / "summary.json").write_text(json.dumps({"generatedOnly": True, "fixtures": rows}, indent=2) + "\n")
print(json.dumps({key: {"bindingCount": value["bindingCount"], "totalClassBytes": value["totalClassBytes"]} for key, value in rows.items()}, indent=2))
