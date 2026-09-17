#!/usr/bin/env python3
"""Create only trusted generated Java-8 fixtures for Iterable linkage and retained gates.

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
assert out.parent == root / "build" and out.name.startswith("java-diff-mc-iterable-link-fixtures-")
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

def build(label, sources, entries, host_main=None, bootstrap_count=88, resources=None):
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
        for name, data in (resources or {}).items():
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    assert resources is None or len(resources) <= 1
    row = {
        "entries": entries, "bindingCount": len(entries), "bootstrapCount": bootstrap_count,
        "selectedResource": next(iter(resources), None) if resources else None,
        "selectedResourceBytes": len(next(iter(resources.values()))) if resources else 0,
        "selectedResourceSHA256": hashlib.sha256(next(iter(resources.values()))).hexdigest() if resources else None,
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
    units = text.encode("utf-16-be", "surrogatepass")
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

# startsWith(String) is the new ordinary offset-zero String surface. Each
# witness is a Java-8 host oracle as well as an EVM fixture. The lone surrogate
# prefix proves UTF-16 *code unit* comparison without adding an offset overload.
def starts_with(label, receiver, prefix, expected):
    build(label, {
        "StartsWithMain.java": """public final class StartsWithMain {
  static int result;
  public static void main(String[] ignored) {
    String receiver = %s;
    String prefix = %s;
    if (receiver.startsWith(prefix) != %s) throw new Error();
    result = 7;
  }
}
""" % (java_literal(receiver), java_literal(prefix), "true" if expected else "false"),
    }, ["StartsWithMain.class"], "StartsWithMain")

starts_with("starts-empty-prefix", "abc", "", True)
starts_with("starts-longer-prefix", "ab", "abc", False)
starts_with("starts-exact", "abc", "abc", True)
starts_with("starts-prefix", "abc", "ab", True)
starts_with("starts-absent", "abc", "ac", False)
starts_with("starts-empty-receiver", "", "", True)
starts_with("starts-empty-receiver-nonempty", "", "x", False)
starts_with("starts-utf16", "Ωx", "Ω", True)
starts_with("starts-surrogate-pair", "😀x", "😀", True)
starts_with("starts-high-surrogate", "\ud83d\ude00x", "\ud83d", True)

# The first bytecode operation in the guest method is prefix.length(); null
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

build("starts-null", {
    "StartsWithNullMain.java": """public final class StartsWithNullMain {
  static int result;
  public static void main(String[] ignored) {
    try { "x".startsWith((String) null); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["StartsWithNullMain.class"], "StartsWithNullMain")

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
}, ["RawObjectGetClassMain.class", "java/lang/Object.class"], bootstrap_count=87)

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

# One generated deflated ZIP entry is the only selected resource. The guest
# reaches it through ClassLoader enumeration -> URL -> ordinary FileInputStream;
# fixture creation supplies archive bytes only and never parses or injects them.
url_resource_name = "generated/url.bin"
url_resource_bytes = bytes([65, 0, 127, 255, 42])
build("url-openstream", {
    "UrlOpenStreamMain.java": """import java.io.*; import java.net.URL; import java.util.Enumeration;
public final class UrlOpenStreamMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    if (UrlOpenStreamMain.class.getClassLoader() == null) throw new Error();
    Enumeration<URL> all = ClassLoader.getSystemClassLoader().getResources("generated/url.bin");
    if (!all.hasMoreElements()) throw new Error();
    URL url = all.nextElement();
    if (all.hasMoreElements() || !url.toString().equals("generated/url.bin")) throw new Error();
    InputStream in = url.openStream();
    if (in.read() != 65 || in.read() != 0 || in.read() != 127 || in.read() != 255 || in.read() != 42 || in.read() != -1) throw new Error();
    in.close();
    try { in.read(); throw new Error(); } catch (IOException expected) {}
    try { new FileOutputStream(new File("/ro/generated/url.bin")).close(); throw new Error(); }
    catch (FileNotFoundException expected) {}
    InputStream again = url.openStream();
    if (again.read() != 65 || again.read() != 0 || again.read() != 127 || again.read() != 255 || again.read() != 42 || again.read() != -1) throw new Error();
    again.close(); result = 7;
  }
}
""",
}, ["UrlOpenStreamMain.class"], resources={url_resource_name: url_resource_bytes})

# The selected resource exists in the generated ZIP, but neither an absent
# enumeration nor direct URL.openStream may synthesize a file or content.
build("url-openstream-absent", {
    "UrlOpenStreamAbsentMain.java": """import java.io.*; import java.net.URL; import java.util.Enumeration;
public final class UrlOpenStreamAbsentMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    if (UrlOpenStreamAbsentMain.class.getClassLoader() == null) throw new Error();
    Enumeration<URL> all = ClassLoader.getSystemClassLoader().getResources("generated/absent.bin");
    if (all.hasMoreElements()) throw new Error();
    try { new URL("generated/absent.bin").openStream(); throw new Error(); }
    catch (FileNotFoundException expected) { result = 7; }
  }
}
""",
}, ["UrlOpenStreamAbsentMain.class"], resources={url_resource_name: url_resource_bytes})

# The measured Properties resource is deliberately small but exercises CRLF/LF,
# leading whitespace, #/! comments, =/:/first-whitespace separators, and
# whitespace adjacent to separators. It has exactly three simple properties.
properties_resource_name = "generated/properties.txt"
properties_resource_bytes = (
    b"# generated comment\r\n"
    b" ! second generated comment\n"
    b"  first = one\r\n"
    b"second :\t two\n"
    b"third \t three\r\n"
)
build("properties-load", {
    "PropertiesLoadMain.java": """import java.io.*; import java.net.URL; import java.util.*;
public final class PropertiesLoadMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    // Materialize this raw class's canonical defining-loader mirror before the
    // system-loader native is used; the resource path must not rely on a
    // loader/mirror state that raw bytecode never created.
    if (PropertiesLoadMain.class.getClassLoader() == null) throw new Error();
    Enumeration<URL> all = ClassLoader.getSystemClassLoader().getResources("generated/properties.txt");
    if (!all.hasMoreElements()) throw new Error();
    URL url = all.nextElement();
    if (all.hasMoreElements() || !url.toString().equals("generated/properties.txt")) throw new Error();
    InputStream input = url.openStream();
    Properties properties = new Properties();
    properties.load(input);
    if (!"one".equals(properties.getProperty("first"))) throw new Error();
    if (!"two".equals(properties.getProperty("second"))) throw new Error();
    if (!"three".equals(properties.getProperty("third"))) throw new Error();
    if (input.read() != -1) throw new Error();
    input.close();
    try { input.read(); throw new Error(); } catch (IOException expected) {}
    result = 7;
  }
}
""",
}, ["PropertiesLoadMain.class"], resources={properties_resource_name: properties_resource_bytes})

# Null is a normal guest invokevirtual boundary, not a native/parser special case.
build("properties-load-null", {
    "PropertiesLoadNullMain.java": """import java.util.Properties;
public final class PropertiesLoadNullMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    try { new Properties().load((java.io.InputStream) null); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["PropertiesLoadNullMain.class"])

# A selected immutable resource carries an unsupported backslash. The ordinary
# parser must raise IOException before it creates a fabricated property value.
build("properties-load-escape", {
    "PropertiesLoadEscapeMain.java": """import java.io.*; import java.net.URL; import java.util.Properties;
public final class PropertiesLoadEscapeMain {
  static int result;
  public static void main(String[] ignored) throws Exception {
    Properties properties = new Properties();
    InputStream input = new URL("generated/unsupported.properties").openStream();
    try { properties.load(input); throw new Error(); }
    catch (IOException expected) {}
    if (properties.getProperty("bad") != null) throw new Error();
    input.close(); result = 7;
  }
}
""",
}, ["PropertiesLoadEscapeMain.class"], resources={"generated/unsupported.properties": b"bad=not\\supported\n"})

# The accepted selected-resource cap permits one exact 4096-unit logical line.
# It remains a direct/reopen boundary because q1 wrapper chains are reserved for
# the small measured resource above.
build("properties-load-line-4096", {
    "PropertiesLoadLine4096Main.java": """import java.io.*; import java.net.URL; import java.util.*;
public final class PropertiesLoadLine4096Main {
  static int result;
  public static void main(String[] ignored) throws Exception {
    // As in the small selected-resource path, the raw main materializes its
    // defining-loader mirror before materializing the system loader.
    if (PropertiesLoadLine4096Main.class.getClassLoader() == null) throw new Error();
    Enumeration<URL> all = ClassLoader.getSystemClassLoader().getResources("generated/line-4096.properties");
    if (!all.hasMoreElements()) throw new Error();
    InputStream input = all.nextElement().openStream();
    Properties properties = new Properties(); properties.load(input);
    if (properties.getProperty("k").length() != 4094 || input.read() != -1) throw new Error();
    input.close(); result = 7;
  }
}
""",
}, ["PropertiesLoadLine4096Main.class"], resources={"generated/line-4096.properties": b"k=" + b"x" * 4094})

# A generated InputStream proves the parser's independent 4097-unit line guard;
# coordinator resource-size validation cannot stand in for this guest check.
build("properties-load-line-4097", {
    "PropertiesLoadLine4097Main.java": """import java.io.*; import java.util.Properties;
public final class PropertiesLoadLine4097Main {
  static int result;
  static final class LongInput extends InputStream {
    int at;
    public int read() { if (at == 4097) return -1; ++at; return 'x'; }
  }
  public static void main(String[] ignored) throws Exception {
    Properties properties = new Properties();
    try { properties.load(new LongInput()); throw new Error(); }
    catch (IOException expected) {}
    if (properties.getProperty("x") != null) throw new Error();
    result = 7;
  }
}
""",
}, ["PropertiesLoadLine4097Main.class", "PropertiesLoadLine4097Main$LongInput.class"])

# Constructor boundaries use an ordinary generated root and a single deflated
# entry. Exactly4096 is valid; DI0 may decode4097 but coordinator construction
# must refuse it before an engine start/head exists.
build("url-resource-4096", {
    "UrlResourceBoundaryMain.java": "public final class UrlResourceBoundaryMain { public static void main(String[] ignored) {} }\n",
}, ["UrlResourceBoundaryMain.class"], resources={"generated/boundary.bin": b"A" * 4096})
build("url-resource-4097", {
    "UrlResourceBoundaryMain.java": "public final class UrlResourceBoundaryMain { public static void main(String[] ignored) {} }\n",
}, ["UrlResourceBoundaryMain.class"], resources={"generated/boundary.bin": b"A" * 4097})

# Exact raw33 and aggregate-byte boundaries exercise this measured cap lift.
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
    row = {"entries": entries, "bindingCount": count, "bootstrapCount": 88, "totalClassBytes": total,
           "classSHA256": {name: hashlib.sha256((classes / name).read_bytes()).hexdigest() for name in entries},
           "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(), "java8HostOracle": target is None}
    (out / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    rows[label] = row

# The focused image has only valueOf(int): every value must be represented by a
# fresh Integer allocation. This intentionally has no host oracle because the
# host Java 8 cache is out of the bounded guest profile.
build("integer-valueof", {
    "IntegerValueOfMain.java": """public final class IntegerValueOfMain {
  static int result;
  public static void main(String[] ignored) {
    int[] values = { -1, 0, Integer.MIN_VALUE, Integer.MAX_VALUE };
    for (int i = 0; i < values.length; ++i) {
      int value = values[i];
      Integer first = Integer.valueOf(value);
      Integer second = Integer.valueOf(value);
      Integer constructed = new Integer(value);
      if (first == null || second == null || constructed == null) throw new Error();
      if (first == second || first == constructed || second == constructed) throw new Error();
      if (first.intValue() != value || second.intValue() != value || constructed.intValue() != value) throw new Error();
      if (!first.equals(second) || !second.equals(constructed) || first.hashCode() != value) throw new Error();
      if (Integer.hashCode(value) != value || Integer.compare(first.intValue(), value) != 0) throw new Error();
    }
    result = 7;
  }
}
""",
}, ["IntegerValueOfMain.class"])

# A root without an Integer symbol must leave the replacement uninitialized.
build("integer-valueof-uninitialized", {
    "IntegerValueOfUninitializedMain.java": """public final class IntegerValueOfUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["IntegerValueOfUninitializedMain.class"], "IntegerValueOfUninitializedMain")

# Bootstrap ownership rejects a raw replacement before guest execution.
build("raw-integer-valueof", {
    "RawIntegerValueOfReplacementMain.java": "public final class RawIntegerValueOfReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/Integer.java": "package java.lang; public final class Integer { public Integer(int value) {} public static Integer valueOf(int value) { return new Integer(value); } }\n",
}, ["RawIntegerValueOfReplacementMain.class", "java/lang/Integer.class"])

# The new ordinary Java-8 overload delegates to the retained decimal parseInt
# method before constructing a guest Integer. This positive witness includes the
# measured provider-priority spelling "10", signs, leading zeroes, and exact bounds.
build("integer-valueof-string-valid", {
    "IntegerValueOfStringValidMain.java": """public final class IntegerValueOfStringValidMain {
  static int result;
  public static void main(String[] ignored) {
    Integer ten = Integer.valueOf("10");
    Integer min = Integer.valueOf("-2147483648");
    Integer max = Integer.valueOf("2147483647");
    Integer plus = Integer.valueOf("+7");
    Integer zero = Integer.valueOf("0000");
    if (ten == null || min == null || max == null || plus == null || zero == null) throw new Error();
    if (ten.intValue() != 10 || min.intValue() != Integer.MIN_VALUE || max.intValue() != Integer.MAX_VALUE) throw new Error();
    if (plus.intValue() != 7 || zero.intValue() != 0 || !ten.equals(new Integer(10)) || ten.hashCode() != 10) throw new Error();
    result = 7;
  }
}
""",
}, ["IntegerValueOfStringValidMain.class"], "IntegerValueOfStringValidMain")

# Empty, sign-only, and non-decimal forms retain the same ordinary guest
# NumberFormatException behavior supplied by the unchanged decimal parseInt.
build("integer-valueof-string-invalid", {
    "IntegerValueOfStringInvalidMain.java": """public final class IntegerValueOfStringInvalidMain {
  static int result;
  private static void reject(String value) {
    try { Integer.valueOf(value); throw new Error(); }
    catch (NumberFormatException expected) { result++; }
  }
  public static void main(String[] ignored) {
    reject(""); reject("+"); reject("-"); reject("12x");
    if (result != 4) throw new Error();
  }
}
""",
}, ["IntegerValueOfStringInvalidMain.class"], "IntegerValueOfStringInvalidMain")

# Null follows the retained parseInt null-to-NumberFormatException behavior,
# rather than a host null branch or a synthetic NPE.
build("integer-valueof-string-null", {
    "IntegerValueOfStringNullMain.java": """public final class IntegerValueOfStringNullMain {
  static int result;
  public static void main(String[] ignored) {
    try { Integer.valueOf((String) null); throw new Error(); }
    catch (NumberFormatException expected) { result = 7; }
  }
}
""",
}, ["IntegerValueOfStringNullMain.class"], "IntegerValueOfStringNullMain")

# Both sides of the signed 32-bit range preserve decimal overflow rejection.
build("integer-valueof-string-overflow", {
    "IntegerValueOfStringOverflowMain.java": """public final class IntegerValueOfStringOverflowMain {
  static int result;
  private static void reject(String value) {
    try { Integer.valueOf(value); throw new Error(); }
    catch (NumberFormatException expected) { result++; }
  }
  public static void main(String[] ignored) {
    reject("2147483648"); reject("-2147483649");
    if (result != 2) throw new Error();
  }
}
""",
}, ["IntegerValueOfStringOverflowMain.class"], "IntegerValueOfStringOverflowMain")

# Only the one-argument String overload is added. Java 8's radix overload must
# stay an ordinary atomic EVM member-resolution refusal; no radix parser is added.
build("integer-valueof-string-radix-omitted", {
    "IntegerValueOfStringRadixOmittedMain.java": """public final class IntegerValueOfStringRadixOmittedMain {
  public static void main(String[] ignored) { Integer.valueOf("10", 10); }
}
""",
}, ["IntegerValueOfStringRadixOmittedMain.class"])

# Collection now genuinely extends the append-only java/lang/Iterable image. The
# returned value crosses a Collection -> Iterable method return, preserves object
# identity, and dispatches the existing concrete HashSet iterator through the new
# interface owner. The host oracle only runs this trusted generated Java-8 source.
build("iterable-link", {
    "IterableLinkMain.java": """import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;
public final class IterableLinkMain {
  static int result;
  static Iterable<Object> pass(Collection<Object> values) { return values; }
  public static void main(String[] ignored) {
    Collection<Object> values = new HashSet<Object>();
    Object item = new Object();
    if (!values.add(item)) throw new Error();
    Iterable<Object> iterable = pass(values);
    if (iterable == null || iterable != values) throw new Error();
    Iterator<Object> iterator = iterable.iterator();
    if (!iterator.hasNext() || iterator.next() != item || iterator.hasNext()) throw new Error();
    result = 7;
  }
}
""",
}, ["IterableLinkMain.class"], "IterableLinkMain")

# A null Collection remains a legal null Iterable return. Calling iterator on a
# null Iterable is the ordinary guest invokeinterface NPE path, not a synthetic
# default-method or host fallback path.
build("iterable-null", {
    "IterableNullMain.java": """import java.util.Collection;
public final class IterableNullMain {
  static int result;
  static Iterable<Object> pass(Collection<Object> values) { return values; }
  public static void main(String[] ignored) {
    if (pass(null) != null) throw new Error();
    Iterable<Object> iterable = null;
    try { iterable.iterator(); throw new Error(); }
    catch (NullPointerException expected) { result = 7; }
  }
}
""",
}, ["IterableNullMain.class"], "IterableNullMain")

# No Iterable symbol use leaves the appended image uninitialized.
build("iterable-uninitialized", {
    "IterableUninitializedMain.java": """public final class IterableUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["IterableUninitializedMain.class"], "IterableUninitializedMain")

# Both hierarchy images are interpreter-owned and cannot be silently supplied as
# raw package members.
build("raw-iterable", {
    "RawIterableReplacementMain.java": "public final class RawIterableReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/Iterable.java": "package java.lang; public interface Iterable<T> {}\n",
}, ["RawIterableReplacementMain.class", "java/lang/Iterable.class"])
build("raw-collection", {
    "RawCollectionReplacementMain.java": "public final class RawCollectionReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/util/Collection.java": "package java.util; public interface Collection<E> {}\n",
}, ["RawCollectionReplacementMain.class", "java/util/Collection.class"])

# Java 8 default Iterable APIs remain outside this narrow hierarchy stage. Both
# bytecode call sites must refuse atomically; no Consumer, Spliterator, stream,
# iteration callback, or fabricated return is added.
build("iterable-foreach-omitted", {
    "IterableForEachOmittedMain.java": """import java.util.HashSet;
public final class IterableForEachOmittedMain {
  public static void main(String[] ignored) {
    Iterable<Object> iterable = new HashSet<Object>();
    iterable.forEach(null);
  }
}
""",
}, ["IterableForEachOmittedMain.class"])
build("iterable-spliterator-omitted", {
    "IterableSpliteratorOmittedMain.java": """import java.util.HashSet;
public final class IterableSpliteratorOmittedMain {
  public static void main(String[] ignored) {
    Iterable<Object> iterable = new HashSet<Object>();
    iterable.spliterator();
  }
}
""",
}, ["IterableSpliteratorOmittedMain.class"])

# The appended Object subclass retains a strong deterministic guest reference:
# get returns precisely the supplied object and null remains null. It has no
# Reference superclass or GC-clearing behavior in this bounded image.
build("weak-reference", {
    "WeakReferenceMain.java": """import java.lang.ref.WeakReference;
public final class WeakReferenceMain {
  static Object retained;
  static int result;
  public static void main(String[] ignored) {
    Object target = new Object();
    WeakReference first = new WeakReference(target);
    WeakReference second = new WeakReference(null);
    if (first == null || second == null) throw new Error();
    if (first.get() != target || first.get() != target) throw new Error();
    if (second.get() != null) throw new Error();
    retained = first.get();
    if (retained != target || retained != first.get()) throw new Error();
    result = 7;
  }
}
""",
}, ["WeakReferenceMain.class"])

# No bytecode symbol use means image87 must not initialize.
build("weak-reference-uninitialized", {
    "WeakReferenceUninitializedMain.java": """public final class WeakReferenceUninitializedMain {
  static int result;
  public static void main(String[] ignored) { result = 7; }
}
""",
}, ["WeakReferenceUninitializedMain.class"], "WeakReferenceUninitializedMain")

# Bootstrap ownership rejects a raw substitution before guest execution.
build("raw-weak-reference", {
    "RawWeakReferenceReplacementMain.java": "public final class RawWeakReferenceReplacementMain { public static void main(String[] ignored) {} }\n",
    "java/lang/ref/WeakReference.java": "package java.lang.ref; public class WeakReference { public WeakReference(Object value) {} public Object get() { return null; } }\n",
}, ["RawWeakReferenceReplacementMain.class", "java/lang/ref/WeakReference.class"])

# The bounded image omits clear and all other Reference APIs. Member resolution
# must refuse atomically rather than offer GC or a Reference fallback.
build("weak-reference-clear-omitted", {
    "WeakReferenceClearOmittedMain.java": """import java.lang.ref.WeakReference;
public final class WeakReferenceClearOmittedMain {
  public static void main(String[] ignored) {
    WeakReference reference = new WeakReference(new Object());
    reference.clear();
  }
}
""",
}, ["WeakReferenceClearOmittedMain.class"])

for count in (29, 30, 31, 32, 33, 34): count_fixture("count-%d" % count, count)
count_fixture("count-33-262158", 33, 262158)
count_fixture("count-33-262159", 33, 262159)
(out / "summary.json").write_text(json.dumps({"generatedOnly": True, "fixtures": rows}, indent=2) + "\n")
print(json.dumps({key: {"bindingCount": value["bindingCount"], "totalClassBytes": value["totalClassBytes"]} for key, value in rows.items()}, indent=2))
